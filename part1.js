const fs = require('fs');
const path = require('path');

const START_DATE = '2002-01-01';
const END_DATE = '2026-01-01';
const LIMIT_PER_REQUEST = 100;
const DATA_DIR = path.join(__dirname, 'data');

if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, {recursive: true}); 
}

// array of YYYYMMDD chunks bc FDA has limit of skipping past 25000 records 
function getMonthlyChunks (start, end) {
    const chunks = [];
    let current = new Date(start);
    const endDate = new Date(end);

    while (current <= endDate) {
        const chunkStart = new Date(current);
        const nextMonth = new Date(current);
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        
        let chunkEnd = new Date(nextMonth);
        chunkEnd.setDate(chunkEnd.getDate() - 1);

        if (chunkEnd > endDate) {
            chunkEnd = new Date(endDate);
        }

        // Change to YYYYMMDD
        const format = (d) => d.toISOString().split('T')[0].replace(/-/g, '');

        chunks.push({
            start: format(chunkStart),
            end: format(chunkEnd)
        });
        
        current = nextMonth;
    }

    return chunks;
}


// backoff to handle 429 error and skip range for 404 error
async function fetchWithRetry(url, retries = 5, backoffs = 2000) {
    for (let i = 0; i < retries; i++) {
        try {
            const response = await fetch(url);

            // skip date range for 404 error
            if (response.status === 404) {
                return null;
            }

            // handle 429 with increasing backoff
            if (response.status === 429) {
                console.warn(`429 Rate limit exceeded, Retrying`);
                await new Promise(resolve => setTimeout(resolve, backoffMs));
                backoffMs *= 2;
                continue;
            }

            // Throw all other errors
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        }

        catch (error) {
            
            // fail if last retry
            if (i === retries - 1) {
                throw new Error(`Failed to fetch ${url}, error: ${error.message}`);
            }
            // else wait and retry
            console.warn(`Network error: ${error.message}`);
            await new Promise(resolve => setTimeout(resolve, backoffMs));
            backoffMs *= 2;
        }
    }       
}