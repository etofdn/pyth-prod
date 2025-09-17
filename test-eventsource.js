// Quick test for EventSource
const EventSource = require('eventsource');
console.log("EventSource type:", typeof EventSource);
console.log("EventSource constructor:", EventSource.constructor);
console.log("Creating test instance...");

try {
    const es = new EventSource('https://httpbin.org/stream/1');
    console.log("✅ EventSource works!");
    es.close();
} catch (e) {
    console.error("❌ EventSource failed:", e.message);
}