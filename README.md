# QA Spec Engine
 [

**AI-powered End-to-End test generator for Quarkus microservices with Kafka.** Describe tests in natural language → Get production-ready `@QuarkusTest` classes with Testcontainers, RestAssured, and Awaitility.

## 🎯 Who Should Use This

**Perfect for:**
- **SDEs/SDETs** writing E2E tests for Quarkus + Kafka microservices
- **Engineering Managers** who want 10x faster test coverage
- **QA Engineers** tired of boilerplate Testcontainers setup
- **DevOps** teams needing regression suites for distributed systems

**Generates tests for:** HTTP APIs, Kafka producers/consumers, hybrid flows (HTTP→Kafka→HTTP).

## 🚀 Quick Start (2 minutes)

```bash
# 1. Clone & setup
git clone <this-repo>
cd qa-spec-engine
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Generate your first test
python main.py -s order-service -c "create new order via HTTP API"

# 3. Copy to Quarkus project
cp generated_tests/*.java /path/to/quarkus-app/src/test/java/
cd /path/to/quarkus-app
mvn quarkus:test
```

**✅ Done!** Production-ready E2E test in `generated_tests/OrderCreateHttpE2ETest.java`.

## 📋 Setup Instructions

### Prerequisites
```
• Python 3.11+
• OpenAI API key (set as OPENAI_API_KEY env var)
• Quarkus project with Testcontainers dependency
```

### Full Setup
```bash
# 1. Clone project
git clone https://github.com/yourorg/qa-spec-engine.git
cd qa-spec-engine

# 2. Create & activate venv
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set OpenAI key
export OPENAI_API_KEY="sk-..."
# Add to ~/.bashrc or use .env file

# 5. Test installation
python main.py --help
```

## 💻 Usage

### Generate Tests
```bash
# HTTP-only test
python main.py -s order-service -c "create new order via POST /api/orders"

# Hybrid HTTP→Kafka test
python main.py -s order-service -c "HTTP order creation publishes OrderCreated Kafka event"

# Pure Kafka test
python main.py -s payment-service -c "PaymentApproved event updates order status"

# Custom model (cheaper/faster)
python main.py -s inventory -c "check stock then create order" --model gpt-4o-mini
```

### Output Files
```
generated_tests/OrderCreateKafkaE2ETest.java     # ✅ Ready-to-run Quarkus test
artifacts/specs.jsonl                           # Data engine (LLM specs)
artifacts/runs.jsonl                            # Execution logs
```

### Copy to Quarkus Project
```bash
cp generated_tests/*.java quarkus-app/src/test/java/com/example/e2e/
cd quarkus-app
mvn quarkus:test
```

## 🌟 Use Cases & Examples

| Scenario | Command | Generated Test |
|----------|---------|----------------|
| **Order Creation (HTTP)** | `python main.py -s order -c "create order"` | `OrderCreateHttpE2ETest.testCreateOrderReturns201` |
| **Event-Driven Flow** | `python main.py -s payment -c "payment approved → order updated"` | `PaymentApprovedKafkaE2ETest.testPaymentApprovedUpdatesOrder` |
| **Hybrid Flow** | `python main.py -s order -c "HTTP order → Kafka event"` | `OrderCreateKafkaE2ETest.testOrderCreationPublishesEvent` |
| **Inventory Check** | `python main.py -s inventory -c "check stock then order"` | `InventoryOrderHybridTest.testStockCheckBeforeOrder` |

## 🏗️ Architecture (Why This Works)

**Software 2.0/1.0 Boundary:**
- **Software 2.0:** LLM generates JSON test spec (probabilistic)
- **Software 1.0:** Jinja2 renders Java (deterministic)
- **Contract:** Versioned JSON Schema v1 (Torvalds data structure)

## 🔧 Customization

### 1. Add OpenAPI Context
Edit `main.py` `ContextSummary`:
```python
http_endpoints=[
    {"method": "POST", "path": "/api/orders", "summary": "Create order"},
    # Add your real OpenAPI paths
]
```

### 2. Extend JSON Schema
`core/schema.py` → Add fields to `TestSpec` model.

### 3. Custom Templates
`templates/QuarkusKafkaTest.java.j2` → Modify test structure.

## 📈 Data Engine 

Every run logs to `artifacts/`:
```
• Spec hash (deduplication)
• Validation errors (prompt improvement)
• Execution results (test flakiness)
```

**Offline analysis:**
```bash
# Find failing specs
jq '.validationErrors != []' artifacts/runs.jsonl

# Find duplicate specs
cut -d, -f3 artifacts/runs.jsonl | sort | uniq -c | sort -nr
```

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `OPENAI_API_KEY` missing | `export OPENAI_API_KEY="sk-..."` |
| Schema validation fails | Check `artifacts/specs.jsonl` for LLM errors |
| Import errors | `sys.path.insert(0, '.')` in `main.py` |
| Tests don't compile | Add Quarkus Testcontainers deps |

## 🎉 Next Steps

1. **Generate 20 tests** for your critical paths
2. **Run in CI** → `mvn surefire-report:report`
3. **Feed failures back** → Improve LLM prompts
4. **Scale up** → Add real OpenAPI parsing

## 🤝 Contributing

1. Fork repo
2. Create feature branch (`git checkout -b feature/add-postgres`)
3. Commit changes (`git commit -m 'Add Postgres container support'`)
4. Push & PR

## 📄 License
MIT - Use freely in commercial projects.

## 🙏 Credits
***

**⭐ Star if this saves you test-writing time!** 🚀