from flask import Flask, render_template, request, jsonify
import requests
import json
import csv
import yfinance as yf
import os

app = Flask(__name__)

# Read the key securely from the server environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# --- 1. LIVE FINANCIAL DATA ---
def get_live_crop_price(crop_name):
    tickers = {"corn": "ZC=F", "wheat": "ZW=F", "soybean": "ZS=F", "cotton": "CT=F", "rice": "ZR=F"} 
    fallback_prices = {"sugarcane": 40.0, "tomato": 350.0, "apple": 800.0, "potato": 250.0, "mango": 600.0, "mangoes": 600.0}
    crop_lower = str(crop_name).lower()
    
    if crop_lower in tickers:
        try:
            ticker = yf.Ticker(tickers[crop_lower])
            recent_data = ticker.history(period="5d") 
            if not recent_data.empty:
                return round(float(recent_data['Close'].iloc[-1]), 2)
        except Exception as e:
            print(f"Finance API Error: {e}")
            
    return fallback_prices.get(crop_lower, 250.00) 

# --- 2. REAL HISTORICAL DATA ---
def get_real_yield_data(target_crop, target_state):
    total_production, total_area = 0, 0
    try:
        with open('india_crop_data.csv', mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get('State_Name', '').strip().lower() == target_state.lower() and \
                   row.get('Crop', '').strip().lower() == target_crop.lower():
                    try:
                        total_area += float(row['Area'])
                        total_production += float(row['Production'])
                    except (ValueError, TypeError):
                        continue
            
            if total_area > 0:
                return round(total_production / total_area, 2)
    except FileNotFoundError:
        pass 
    
    fallbacks = {"sugarcane": 35.0, "tomato": 15.0, "cotton": 1.2, "rice": 2.5, "wheat": 2.2, "corn": 3.0, "apple": 8.0, "potato": 10.0, "mango": 4.5, "mangoes": 4.5}
    return fallbacks.get(target_crop.lower(), 2.0)

# --- 3. REAL AI AGENT ---
def call_real_ai(user_message, current_state, is_dropdown_update=False):
    if not GROQ_API_KEY or "YOUR_ACTUAL_KEY" in GROQ_API_KEY:
        return {"error": True, "reply": "⚠️ Error: You must paste your real Groq API key in app.py!"}
    system_prompt = """
    You are an expert AgTech AI Agronomist for India.
    
    CRITICAL RULE: The user will provide their current "profile" and a "message". If their message mentions a NEW crop (e.g. "rice", "wheat"), a NEW state, or a NEW area, you MUST update the "crop", "state", or "area" fields in your JSON output to reflect their new choice! Do not ignore their new input.
    
    Task 1: Evaluate if the active crop can realistically and commercially be grown in the active state. Set "is_suitable" to true or false.
    
    Task 2 (ATTRACTIVE FORMATTING):
    - If "is_suitable" is true: Provide 3 actionable suggestions to maximize yield. Format the "reply" beautifully using HTML. Use `<ul class='list-disc pl-5 mt-2 space-y-2'>` for your list, `<li>` for each point, and `<strong>` to highlight key terms.
    - If "is_suitable" is false: DO NOT provide growing tips. Explain why the climate is incompatible, and suggest 2 alternative crops. Use `<br><br>` for paragraph spacing and `<strong>` for emphasis.
    
    You MUST output ONLY valid JSON format exactly like this:
    {"state": "...", "experience": "...", "crop": "...", "area": 0, "is_suitable": true, "reply": "..."}
    """

    if is_dropdown_update:
        user_msg = f"My profile: {json.dumps(current_state)}. Analyze suitability and generate yield tips."
    else:
        user_msg = f"My profile: {json.dumps(current_state)}. Message: '{user_message}'"

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions", 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_msg}], "response_format": {"type": "json_object"}, "temperature": 0.4}
        )
        response.raise_for_status()
        return json.loads(response.json()['choices'][0]['message']['content'])
    except Exception as e:
        print(f"General AI Error: {e}")
        return {"error": True, "reply": "AI Agent offline. Please check terminal."}

# --- ROUTES ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    current_state = data.get('current_state', {})
    is_dropdown_update = data.get('is_dropdown_update', False)
    user_message = data.get('message', '')
    
    ai_response = call_real_ai(user_message, current_state, is_dropdown_update)
    
    reply = ai_response.get("reply", "Sorry, I encountered an error.")
    is_suitable = ai_response.get("is_suitable", True)
    
    ui_data = {
        "state": ai_response.get("state") or current_state.get("state"),
        "experience": ai_response.get("experience") or current_state.get("experience"),
        "crop": ai_response.get("crop") or current_state.get("crop"),
        "area": current_state.get("area") or ai_response.get("area") or 0,
        "estimated_profit": "--",
        "total_yield": "--"
    }
    
    # Safely convert area to a number to prevent math crashes
    try:
        farm_area = float(ui_data["area"])
    except (ValueError, TypeError):
        farm_area = 0.0
    
    # Check if we have valid data and an area greater than 0
    if ui_data.get("crop") and ui_data.get("state") and farm_area > 0:
        if not is_suitable:
            ui_data["estimated_profit"] = "₹0.00"
            ui_data["total_yield"] = "0 Tons"
            reply += f"<br><br><span class='text-red-600 font-bold bg-red-50 p-2 rounded block border border-red-200'><i class='fa-solid fa-triangle-exclamation mr-2'></i>WARNING: Prediction halted. {ui_data['crop'].title()} is not climatically suited for commercial farming in {ui_data['state']}.</span>"
        else:
            live_price_usd = get_live_crop_price(ui_data["crop"])
            historical_yield = get_real_yield_data(ui_data["crop"], ui_data["state"])
            
            if live_price_usd and historical_yield:
                live_price_inr = live_price_usd * 83.0
                total_yield = farm_area * historical_yield
                total_profit_inr = total_yield * live_price_inr
                
                ui_data["estimated_profit"] = f"₹{total_profit_inr:,.2f}"
                ui_data["total_yield"] = f"{total_yield:,.2f} Tons"
                reply += f"<br><br><span class='text-emerald-700 text-sm font-semibold'><i class='fa-solid fa-chart-simple mr-1'></i> Live Market Data: Trading at ₹{live_price_inr:,.2f}/ton. Regional average yield is {historical_yield} tons/acre.</span>"

    return jsonify({"reply": reply, "ui_data": ui_data})

if __name__ == '__main__':
    app.run(debug=True, port=5000)