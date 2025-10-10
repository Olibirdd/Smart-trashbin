const leaderboardBody = document.getElementById('leaderboardBody');
const spinner = document.getElementById('spinner');

async function fetchLeaderboard() {
    spinner.style.display = 'block';
    
    try {
        const response = await fetch('/api/leaderboard');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();

        // Debugging: see what data looks like
        console.log("📊 Raw leaderboard data:", data);

        // Clear existing content
        leaderboardBody.innerHTML = '';
        
        if (data.leaderboard && data.leaderboard.length > 0) {
            data.leaderboard.forEach((user, index) => {
                console.log(`👤 User ${index + 1}:`, user); // print each user

                const row = document.createElement('tr');
                
                // Add special styling for top 3 users
                if (index < 3) {
                    row.classList.add('top-user');
                }
                
                // ✅ Correct fields
                const rank = index + 1;
                const username = user.username || "Unknown";
                const bottleCount = user.bottle_count ?? 0;  // use your backend field

                row.innerHTML = `
                    <td><span class="rank-badge">${rank}</span></td>
                    <td>${username}</td>
                    <td>${bottleCount}</td>
                `;
                
                leaderboardBody.appendChild(row);
            });
        } else {
            // Show message if no data available
            const row = document.createElement('tr');
            row.innerHTML = `
                <td colspan="3" style="text-align: center; padding: 2rem; color: #666;">
                    No leaderboard data available yet
                </td>
            `;
            leaderboardBody.appendChild(row);
        }
    } catch (error) {
        console.error('❌ Failed to fetch leaderboard:', error);
        
        // Show error message
        leaderboardBody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; padding: 2rem; color: #d32f2f;">
                    Error loading leaderboard. Please try again later.
                </td>
            </tr>
        `;
    } finally {
        spinner.style.display = 'none';
    }
}

// Initialize the leaderboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    fetchLeaderboard();
});

// Refresh leaderboard every 30 seconds
setInterval(fetchLeaderboard, 30000);
