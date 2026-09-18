const fs = require('fs');
const path = require('path');

const CONCURRENCY_LIMIT = 3;
const START_DATE = '2002-01-01';
const END_DATE = '2026-01-01';
const LIMIT_PER_REQUEST = 100;
const DATA_DIR = path.join(__dirname, 'data');

if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR, {recursive: true}); 
}


async function main() {
    console.log(`Date Range: ${START_DATE} to ${END_DATE}`);
    console.log(`Concurrency Limit: ${CONCURRENCY_LIMIT}`);

    const dateChunks = getMonthlyChunks(START_DATE, END_DATE);
    const downloadTasks = [];
    
    // find # of records for each month
    await processQueue(dateChunks, CONCURRENCY_LIMIT, async (chunk) => {
        const url = `https://api.fda.gov/food/event.json?search=date_started:[${chunk.start}+TO+${chunk.end}]&limit=1`;
        const data = await fetchWithRetry(url);

        if (data && data.meta && data.meta.results) {
            const total = data.meta.results.total;

            // download task for every 100 records
            for (let skip = 0; skip < total; skip += LIMIT_PER_REQUEST) {
                downloadTasks.push({
                    start: chunk.start,
                    end: chunk.end,
                    skip: skip
                });
            }
        }
    });

    console.log(`Downloading`);
    
    let completed = 0;

    await processQueue(downloadTasks, CONCURRENCY_LIMIT, async (task) => {
        const url = `https://api.fda.gov/food/event.json?search=date_started:[${task.start}+TO+${task.end}]&limit=${LIMIT_PER_REQUEST}&skip=${task.skip}`;
        const data = await fetchWithRetry(url);

        if (data && data.results) {
            const fileName = `food_events_${task.start}_${task.end}_skip_${task.skip}.json`;
            const filePath = path.join(DATA_DIR, fileName);

            // save to disk
            fs.writeFileSync(filePath, JSON.stringify(data.results, null, 2), 'utf-8');

            completed++;
            if (completed % 25 === 0 || completed === downloadTasks.length) {
                console.log(`Progress: ${completed} / ${downloadTasks.length} batches downloaded`);
            }
        }
    });

    console.log(`Done, saved to ./data`);
}


// Process array of tasks with concurrency limit
async function processQueue(tasks, concurrencyLimit, processor) {
    let currentIndex = 0;

    const worker = async (workerId) => {
        while (currentIndex < tasks.length) {
            const taskIndex = currentIndex++;
            const task = tasks[taskIndex];
            // wait for curr task before getting next
            await processor(task, workerId);
        }
    }

    // concurrencyLimit number of workers
    const workers = [];
    for (let i = 0; i < concurrencyLimit; i++) {
        workers.push(worker(i));
    }

    await Promise.all(workers);
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