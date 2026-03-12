/**
 * Redis + SuperBrain Node.js Symbiosis Demo
 * 
 * Demonstrates how a Node.js agent utilizes the SuperBrain 
 * Data Plane for high-frequency intake and Redis for 
 * global coordination.
 * 
 * Setup: npm install superbrain-distributed-sdk redis
 */

const { Client } = require('superbrain-distributed-sdk');
const redis = require('redis');

async function runSymbioticAgent() {
    // 1. Connect to Redis (Control Plane)
    const redisClient = redis.createClient({ url: 'redis://localhost:6379' });
    await redisClient.connect();
    console.log('🔄 [Redis] Control Plane Connected.');

    // 2. Connect to SuperBrain (Data Plane)
    // DistributedContextFabric interface in Node.js
    const fabric = new Client('localhost:60050');
    console.log('🧠 [SuperBrain] Data Plane Linked.');

    // Function to process ticks from shared memory
    const processTick = async () => {
        try {
            // Allocate a pointer or search for existing context
            // In Node.js SDK, we use the Client to manage pointers directly
            const ptrId = "latest_market_tick"; // Hypothetical shared pointer
            const data = await fabric.read(ptrId, 0, 1024);

            if (data && data.length > 0) {
                const tick = JSON.parse(data.toString());
                console.log(`📈 [SuperBrain] Recieved: ${tick.symbol} @ $${tick.price}`);

                // Coordination Step: Global Rate Limit Check
                const canTrade = await redisClient.set('global_throttle', 'active', {
                    NX: true,
                    EX: 1
                });

                if (canTrade) {
                    console.log('⚡ [Redis] Rate Limit Check Passed. Executing Step...');
                } else {
                    console.log('⏸ [Redis] Throttled by Global Control Plane.');
                }
            }
        } catch (err) {
            // Handle scenario where pointer isn't ready or network latency occurs
            console.log('... Awaiting new data on the fabric ...');
        }
    };

    // Run high-frequency loop
    setInterval(processTick, 500);
}

runSymbioticAgent().catch(console.error);
