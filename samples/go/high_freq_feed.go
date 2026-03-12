package main

import (
	"fmt"
	"log"
	"time"

	"github.com/user/superbrain/pkg/sdk"
)

// HighFreqFeed demonstrates using SuperBrain's microsecond data plane
// for high-frequency market data distribution.
func main() {
	coordinator := "localhost:60050"

	// 1. Initialize High-Performance Client
	client, err := sdk.NewClient(coordinator)
	if err != nil {
		log.Fatalf("Failed to connect to SuperBrain: %v", err)
	}

	// 2. Security: Enroll in the Fabric (mTLS setup)
	err = client.Register("go-high-freq-node")
	if err != nil {
		log.Fatalf("Registration failed: %v", err)
	}

	// 3. Allocate Shared memory for a Market Feed
	// 4MB pointer for high-speed writes
	ptr, err := client.Allocate(4 * 1024 * 1024)
	if err != nil {
		log.Fatalf("Allocation failed: %v", err)
	}
	fmt.Printf("🚀 Market Feed Context Initialized: %s\n", ptr.ID)

	// 4. High-Frequency Write Loop (Simulated Ticks)
	go func() {
		for i := 0; ; i++ {
			tick := []byte(fmt.Sprintf(`{"symbol": "SBUSD", "price": 13.5, "ts": %d}`, time.Now().UnixNano()))
			
			// Write to the fabric with microsecond fan-out
			err := client.Write(ptr, 0, tick)
			if err != nil {
				log.Printf("Write error: %v", err)
			}
			
			if i%100 == 0 {
				fmt.Printf("📈 [Go] Published %d ticks to shared fabric...\n", i)
			}
			time.Sleep(100 * time.Millisecond)
		}
	}()

	// 5. High-Frequency Read (Simulated Secondary Strategy)
	// This would typically be in another process/machine.
	for {
		data, err := client.Read(ptr, 0, 1024)
		if err == nil && len(data) > 0 {
			// Process tick data instantly from shared memory
			// fmt.Printf("📥 [Go] Recalled latest tick data: %s\n", string(data))
		}
		time.Sleep(500 * time.Millisecond)
	}
}
