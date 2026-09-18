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