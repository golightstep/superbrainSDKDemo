/**
 * Collective Intelligence: Multi-Agent Shared Memory Pattern (Node.js)
 * 
 * Demonstrates the "connective tissue" pattern where different 
 * Node.js agents share a high-performance distributed context.
 * 
 * Setup: npm install superbrain-distributed-sdk
 */

const { Client } = require('superbrain-distributed-sdk');

async function runCollectiveMemoryDemo() {
    // 1. Initialize the Shared Intelligence Fabric
    const fabric = new Client('localhost:60050');
    console.log('🧠 [SuperBrain] Collective Fabric Initialized.');

    /**
     * Agent Alpha: The Researcher
     * Persists findings to the distributed fabric.
     */
    const agentAlpha = {
        saveDiscovery: async (fact) => {
            const ptrId = `discovery_${Date.now()}`;
            const data = Buffer.from(JSON.stringify({
                body: fact,
                timestamp: new Date().toISOString(),
                source: 'Agent Alpha'
            }));
            await fabric.write(ptrId, 0, data);
            console.log(`✅ Agent Alpha: Persisted discovery into shared fabric.`);
        }
    };

    /**
     * Agent Beta: The Analyst
     * Recalls findings from the fabric without direct communication with Alpha.
     */
    const agentBeta = {
        analyzeHistory: async () => {
            console.log('🔍 Agent Beta: Querying collective memory...');
            // In a real scenario, Beta would iterate over known pointers 
            // or use a discovery mechanism provided by the SuperBrain Coordinator.
            const knownPtr = "latest_discovery"; // Hypothetical shared key
            try {
                const raw = await fabric.read(knownPtr, 0, 1024);
                const memory = JSON.parse(raw.toString());
                console.log(`📥 Agent Beta Recalled: "${memory.body}" from ${memory.source}`);
            } catch (e) {
                console.log('... Awaiting shared context synchronization ...');
            }
        }
    };

    // Simulate the flow
    await agentAlpha.saveDiscovery("SuperBrain fan-out latency verified at 13.5μs.");
    setTimeout(async () => {
        await agentBeta.analyzeHistory();
    }, 1000);
}

runCollectiveMemoryDemo().catch(console.error);
