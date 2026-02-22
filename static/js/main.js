let myChart;

async function predictYield() {
    // 1. Get input values
    const payload = {
        n: parseInt(document.getElementById('n-input').value),
        p: parseInt(document.getElementById('p-input').value),
        k: parseInt(document.getElementById('k-input').value),
        ph: parseFloat(document.getElementById('ph-input').value),
        rain: parseInt(document.getElementById('rain-input').value),
        temp: parseInt(document.getElementById('temp-input').value)
    };

    try {
        // 2. Send data to Flask Backend
        const response = await fetch('/api/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        // 3. Unhide results section
        document.getElementById('results-section').classList.remove('hidden');

        // 4. Update KPI Cards
        document.getElementById('yield-output').innerText = data.estimated_yield + ' Tons/ha';
        document.getElementById('profit-output').innerText = '$' + data.potential_profit.toLocaleString('en-US');

        // 5. Update Chart
        updateChart(payload.n, payload.p, payload.k);

        // 6. Update AI Insights from Backend
        const insightsContainer = document.getElementById('ai-insights');
        insightsContainer.innerHTML = ''; 
        
        data.insights.forEach(text => {
            let li = document.createElement('li');
            li.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong class="text-emerald-900 font-bold">$1</strong>');
            insightsContainer.appendChild(li);
        });

    } catch (error) {
        console.error("Error communicating with the backend:", error);
        alert("Failed to fetch prediction. Is the Flask server running?");
    }
}

function updateChart(n, p, k) {
    const ctx = document.getElementById('soilChart').getContext('2d');
    const idealData = [90, 60, 50]; 

    if (myChart) {
        myChart.destroy(); 
    }

    myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Nitrogen (N)', 'Phosphorus (P)', 'Potassium (K)'],
            datasets: [
                {
                    label: 'Your Soil Input',
                    data: [n, p, k],
                    backgroundColor: '#065f46', 
                    borderRadius: 4
                },
                {
                    label: 'Ideal Baseline',
                    data: idealData,
                    backgroundColor: '#d97706', 
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}