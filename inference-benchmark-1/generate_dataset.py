"""
generate_dataset.py
Generates a synthetic benchmark dataset (test_dataset.jsonl) with
prompts across 5 token-length categories for vLLM /v1/completions testing.
"""

import json
import random

random.seed(42)

# Prompt templates per category
TEMPLATES = {
    "short": [
        "What is {topic}?",
        "Explain {topic} in one sentence.",
        "Define {topic}.",
        "What are the main uses of {topic}?",
        "Give a brief overview of {topic}.",
    ],
    "medium": [
        "Summarize the key concepts of {topic} in a few paragraphs.",
        "Compare and contrast {topic_a} and {topic_b}.",
        "Explain how {topic} works, including its main components.",
        "What are the advantages and disadvantages of {topic}?",
        "Describe the history and evolution of {topic}.",
    ],
    "long": [
        "Write a detailed technical explanation of {topic}, covering its architecture, "
        "use cases, limitations, and best practices. Include examples where relevant.",
        "Provide a comprehensive analysis of {topic_a} versus {topic_b}, discussing "
        "performance, scalability, cost, and developer experience in depth.",
        "Explain the end-to-end workflow of {topic} in a production environment, "
        "including setup, configuration, monitoring, and common failure modes.",
    ],
    "xl": [
        "You are a senior software engineer. A junior developer has asked you to review "
        "the following design document for a new {topic} system. The document describes "
        "the architecture, data flow, API contracts, and deployment strategy. Please "
        "provide detailed feedback covering correctness, scalability, security, "
        "observability, and any missing considerations. Be thorough and specific. "
        "Design document: [The system uses a microservices architecture with {topic} "
        "at its core. Services communicate via REST APIs. Data is stored in PostgreSQL "
        "with Redis for caching. The deployment target is Kubernetes on AWS EKS. "
        "Authentication uses JWT tokens. Logging is handled by Fluentd to Elasticsearch.]",
        "You are an expert in {topic}. A team is migrating their legacy monolith to a "
        "modern {topic}-based architecture. They have the following constraints: "
        "zero downtime migration, existing PostgreSQL database must be retained, "
        "team has 3 backend engineers and 2 months timeline. Please provide a "
        "step-by-step migration plan with risk mitigation strategies, rollback procedures, "
        "and success metrics for each phase of the migration.",
    ],
    "xxl": [
        "You are a principal architect at a large tech company. The CTO has asked you "
        "to produce a comprehensive technical strategy document for adopting {topic} "
        "across the organization. The company has 500 engineers, 200 microservices, "
        "processes 10M requests/day, and operates in 3 AWS regions. The document must "
        "cover: (1) Executive summary and business justification, (2) Current state "
        "assessment and gap analysis, (3) Target architecture with diagrams described "
        "in text, (4) Phased implementation roadmap over 18 months, (5) Team structure "
        "and skill requirements, (6) Risk register with mitigation strategies, "
        "(7) Cost-benefit analysis with rough estimates, (8) Success metrics and KPIs, "
        "(9) Vendor evaluation criteria if applicable, (10) Governance and compliance "
        "considerations. Be specific, actionable, and realistic given the constraints.",
    ],
}

TOPICS = [
    "Kubernetes", "Redis", "PostgreSQL", "Kafka", "GraphQL",
    "gRPC", "Terraform", "Prometheus", "Elasticsearch", "Nginx",
    "Docker", "Istio", "Argo CD", "Vault by HashiCorp", "Envoy Proxy",
    "Apache Spark", "Flink", "Airflow", "dbt", "Snowflake",
]

TOPIC_PAIRS = [
    ("REST", "GraphQL"), ("Kafka", "RabbitMQ"), ("PostgreSQL", "MongoDB"),
    ("Kubernetes", "Docker Swarm"), ("Redis", "Memcached"),
    ("gRPC", "REST"), ("Terraform", "Pulumi"), ("Prometheus", "Datadog"),
]

CATEGORIES = {
    "short":  {"max_tokens": 128,  "count": 40},
    "medium": {"max_tokens": 256,  "count": 40},
    "long":   {"max_tokens": 512,  "count": 40},
    "xl":     {"max_tokens": 512,  "count": 40},
    "xxl":    {"max_tokens": 512,  "count": 40},
}


def build_prompt(category: str) -> str:
    template = random.choice(TEMPLATES[category])
    if "{topic_a}" in template and "{topic_b}" in template:
        pair = random.choice(TOPIC_PAIRS)
        return template.format(topic_a=pair[0], topic_b=pair[1])
    return template.format(topic=random.choice(TOPICS))


def main():
    records = []
    for category, cfg in CATEGORIES.items():
        for _ in range(cfg["count"]):
            records.append({
                "category": category,
                "prompt": build_prompt(category),
                "max_tokens": cfg["max_tokens"],
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False,
            })

    random.shuffle(records)

    output_path = "test_dataset.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")

    print(f"Generated {len(records)} prompts -> {output_path}")
    for cat in CATEGORIES:
        count = sum(1 for r in records if r["category"] == cat)
        print(f"  {cat}: {count} prompts")


if __name__ == "__main__":
    main()
