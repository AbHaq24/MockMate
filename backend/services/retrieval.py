from dataclasses import dataclass
import re
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class CuratedQuestion:
    topic: str
    difficulty: str
    question: str
    reference_answer: str


# ---------------------------------------------------------------------------
# Curated Question Bank for Data Science & AI Interview Preparation
# ---------------------------------------------------------------------------
CURATED_QUESTION_BANK: list[CuratedQuestion] = [
    # ------------------ Python Programming ------------------
    CuratedQuestion(
        topic="Python",
        difficulty="Easy",
        question="What is the key difference between a Python list and a tuple, and when should you use each?",
        reference_answer=(
            "Lists are mutable (can be modified after creation: appended, edited, resized) "
            "and are defined using square brackets []. Tuples are immutable (cannot be altered after creation) "
            "and use parentheses (). Tuples should be used for heterogeneous fixed collections, dictionary keys, "
            "or data integrity protection. Lists should be used for collections of items that may change during runtime."
        ),
    ),
    CuratedQuestion(
        topic="Python",
        difficulty="Easy",
        question="Explain how Python handles memory for mutable vs immutable objects when passed to a function.",
        reference_answer=(
            "Python uses 'pass-by-object-reference'. If you pass an immutable object (like int, str, tuple) and "
            "modify it inside a function, Python creates a new local object without modifying the caller's value. "
            "If you pass a mutable object (like a list or dict) and mutate it in-place (e.g. list.append()), the "
            "caller's original object will reflect the change."
        ),
    ),
    CuratedQuestion(
        topic="Python",
        difficulty="Medium",
        question="What is a Python generator, how does the 'yield' keyword work, and what is its primary memory advantage?",
        reference_answer=(
            "A generator is a function that produces a sequence of results lazily using the 'yield' statement instead "
            "of 'return'. When 'yield' is executed, the function's state is paused and saved, yielding one value at a time. "
            "The primary advantage is memory efficiency: generators compute items on demand without allocating the entire "
            "collection into memory, which is essential for processing large datasets or infinite streams."
        ),
    ),
    CuratedQuestion(
        topic="Python",
        difficulty="Medium",
        question="Explain how Python decorators work and write the conceptual structure of a decorator that measures execution time.",
        reference_answer=(
            "A decorator is a callable that takes another function as an argument, extends or modifies its behavior without "
            "changing the original source code, and returns a callable. Conceptually: def timer(func): def wrapper(*args, "
            "**kwargs): t0 = time.time(); result = func(*args, **kwargs); print(time.time() - t0); return result; return wrapper. "
            "The @timer syntax provides syntactic sugar for func = timer(func)."
        ),
    ),
    CuratedQuestion(
        topic="Python",
        difficulty="Hard",
        question="What is the Global Interpreter Lock (GIL) in CPython, why was it introduced, and how can CPU-bound tasks bypass it?",
        reference_answer=(
            "The GIL is a mutex that allows only one native thread to execute Python bytecode at a time in CPython. It was "
            "implemented to simplify memory management and protect reference counts from race conditions. For I/O-bound tasks, "
            "threads release the GIL while waiting. For CPU-bound tasks, the GIL causes multithreading to run serially; "
            "it can be bypassed using the multiprocessing module (separate processes with independent GILs), external C/C++ extensions, "
            "or subinterpreters."
        ),
    ),

    # ------------------ SQL & Databases ------------------
    CuratedQuestion(
        topic="SQL",
        difficulty="Easy",
        question="What is the difference between WHERE and HAVING clauses in SQL, and when must you use HAVING?",
        reference_answer=(
            "WHERE filters individual rows before any grouping or aggregation takes place. HAVING filters aggregated "
            "group rows after the GROUP BY clause has been applied. You must use HAVING whenever your filtering condition "
            "involves an aggregate function (e.g. HAVING COUNT(*) > 5 or HAVING AVG(salary) >= 50000)."
        ),
    ),
    CuratedQuestion(
        topic="SQL",
        difficulty="Easy",
        question="Explain the difference between an INNER JOIN, LEFT JOIN, and FULL OUTER JOIN.",
        reference_answer=(
            "INNER JOIN returns only rows where there is a match in both tables. LEFT JOIN returns all rows from the left "
            "table and matched rows from the right table, placing NULLs in right-table columns when no match exists. "
            "FULL OUTER JOIN returns all rows from both tables, filling with NULL on either side where a match is absent."
        ),
    ),
    CuratedQuestion(
        topic="SQL",
        difficulty="Medium",
        question="Explain the difference between ROW_NUMBER(), RANK(), and DENSE_RANK() window functions with duplicate values.",
        reference_answer=(
            "All three assign ranks within a partition ordered by specified columns. ROW_NUMBER() assigns strictly consecutive, "
            "unique integers (1, 2, 3, 4) arbitrarily breaking ties. RANK() assigns the same rank to ties but skips subsequent ranks "
            "(e.g., 1, 2, 2, 4). DENSE_RANK() assigns the same rank to ties but never skips ranks (e.g., 1, 2, 2, 3)."
        ),
    ),
    CuratedQuestion(
        topic="SQL",
        difficulty="Medium",
        question="What is database indexing, how does a B-Tree index speed up queries, and what is the trade-off of having too many indexes?",
        reference_answer=(
            "A database index is a data structure (commonly a balanced B-Tree) that allows logarithmic O(log N) lookup time for "
            "matching rows rather than full table scans O(N). The trade-offs of excessive indexing include increased disk storage "
            "and slower write operations (INSERT, UPDATE, DELETE), because every index must be synchronously updated on data changes."
        ),
    ),
    CuratedQuestion(
        topic="SQL",
        difficulty="Hard",
        question="Explain the four ACID properties in relational database transactions and provide a concrete failure scenario that 'Isolation' prevents.",
        reference_answer=(
            "ACID stands for Atomicity (all-or-nothing execution), Consistency (transactions preserve schema rules/constraints), "
            "Isolation (concurrent transactions execute independently without interference), and Durability (committed changes persist "
            "across crashes). Isolation prevents race conditions such as 'dirty reads' (reading uncommitted data that later rolls back) "
            "and 'lost updates' (two transactions overwriting the same balance simultaneously)."
        ),
    ),

    # ------------------ Machine Learning ------------------
    CuratedQuestion(
        topic="Machine Learning",
        difficulty="Easy",
        question="What is the difference between supervised, unsupervised, and reinforcement learning?",
        reference_answer=(
            "Supervised learning trains on labeled datasets (features paired with known target ground truth) for classification "
            "or regression. Unsupervised learning discovers hidden patterns, clusters, or representations in unlabeled data "
            "(e.g. K-Means, PCA). Reinforcement learning trains agents to make sequential decisions by taking actions in an "
            "environment to maximize cumulative scalar rewards."
        ),
    ),
    CuratedQuestion(
        topic="Machine Learning",
        difficulty="Easy",
        question="What is overfitting in machine learning, and what are two common symptoms indicating a model is overfitted?",
        reference_answer=(
            "Overfitting occurs when a model learns training noise and idiosyncrasies rather than generalizable underlying patterns. "
            "Two primary symptoms are: (1) high training accuracy / near-zero training error paired with significantly lower validation/test "
            "performance, and (2) high variance across different training data splits."
        ),
    ),
    CuratedQuestion(
        topic="Machine Learning",
        difficulty="Medium",
        question="Explain the Bias-Variance tradeoff and describe how model complexity influences both error components.",
        reference_answer=(
            "Bias error stems from overly simplistic assumptions in the model (underfitting), causing high systematic error on both training "
            "and test data. Variance error stems from sensitivity to small fluctuations/noise in the training set (overfitting). "
            "As model complexity increases, bias decreases while variance increases. Optimal generalization error is achieved at the sweet "
            "spot where total error (Bias² + Variance + Irreducible Noise) is minimized."
        ),
    ),
    CuratedQuestion(
        topic="Machine Learning",
        difficulty="Medium",
        question="Why is accuracy a misleading metric for imbalanced datasets, and which alternative metrics should you prioritize for fraud detection?",
        reference_answer=(
            "In imbalanced datasets (e.g. 99% non-fraud, 1% fraud), a naive model predicting 'no fraud' achieves 99% accuracy while catching "
            "0 frauds. For fraud detection, one should prioritize Precision (purity of flagged alerts), Recall (fraction of all true frauds caught), "
            "F1-score, and Precision-Recall AUC (PR-AUC), which evaluate positive-class trade-offs regardless of large true negative counts."
        ),
    ),
    CuratedQuestion(
        topic="Machine Learning",
        difficulty="Hard",
        question="Contrast L1 (Lasso) and L2 (Ridge) regularization mathematically and explain why L1 produces sparse coefficients while L2 shrinks them.",
        reference_answer=(
            "Ridge adds an L2 penalty proportional to the sum of squared weights (λ Σ w_i²), while Lasso adds an L1 penalty proportional to the "
            "sum of absolute weights (λ Σ |w_i|). Geometrically, the L1 constraint region is a diamond with sharp corners on the coordinate axes; "
            "the elliptical loss contours frequently intersect these corners, driving non-informative coefficients strictly to zero (feature selection). "
            "L2 has a circular/spherical constraint region without sharp vertices, shrinking coefficients asymptotically toward zero without zeroing them."
        ),
    ),

    # ------------------ Deep Learning & GenAI ------------------
    CuratedQuestion(
        topic="Deep Learning & GenAI",
        difficulty="Easy",
        question="Why is the ReLU activation function widely preferred over Sigmoid in deep feedforward neural networks?",
        reference_answer=(
            "Sigmoid saturates at 0 and 1, producing near-zero derivatives for large positive or negative inputs, which causes "
            "vanishing gradients in deep architectures. ReLU (f(x) = max(0, x)) maintains a constant derivative of 1 for all positive inputs, "
            "enabling robust gradient flow during backpropagation and much faster computational training."
        ),
    ),
    CuratedQuestion(
        topic="Deep Learning & GenAI",
        difficulty="Medium",
        question="Explain the self-attention mechanism in the Transformer architecture and what Query, Key, and Value vectors represent.",
        reference_answer=(
            "Self-attention allows each token in a sequence to dynamically attend to every other token based on contextual relevance. "
            "Each token embedding is projected into Query (what information this token seeks), Key (what information this token offers), "
            "and Value (the actual content representation). Attention weights are computed via softmax(Q·Kᵀ / √d_k) · V, producing a "
            "weighted sum of values that updates token context."
        ),
    ),
    CuratedQuestion(
        topic="Deep Learning & GenAI",
        difficulty="Medium",
        question="What is Retrieval-Augmented Generation (RAG), and what are the key steps in a production RAG pipeline?",
        reference_answer=(
            "RAG grounds LLM generation in external, domain-specific or real-time documents to reduce hallucination. The pipeline steps: "
            "(1) Ingestion: chunk domain documents, generate dense vector embeddings, and store in a vector database; (2) Retrieval: embed user query, "
            "perform approximate nearest neighbor search (cosine similarity) to find top-k relevant chunks; (3) Generation: augment prompt with retrieved "
            "chunks as context and send to the LLM for grounded response synthesis."
        ),
    ),
    CuratedQuestion(
        topic="Deep Learning & GenAI",
        difficulty="Hard",
        question="What does Low-Rank Adaptation (LoRA) do during LLM fine-tuning, and why is it drastically more parameter-efficient than full fine-tuning?",
        reference_answer=(
            "LoRA freezes pretrained model weights W_0 (dim d × k) and injects trainable rank-decomposition matrices A and B (dim d × r and r × k, "
            "where rank r << min(d, k)). During inference, W = W_0 + (B · A). Because r is typically small (e.g., 4 or 8), trainable parameters "
            "are reduced by 99%+, dramatically reducing GPU VRAM requirements and optimizer state memory while preserving model capability."
        ),
    ),

    # ------------------ Statistics & Probability ------------------
    CuratedQuestion(
        topic="Statistics",
        difficulty="Easy",
        question="What is the Central Limit Theorem (CLT) and why is it foundational to inferential statistics?",
        reference_answer=(
            "The Central Limit Theorem states that the distribution of the sample mean approaches a normal distribution as sample size n grows "
            "sufficiently large (typically n >= 30), regardless of the shape of the underlying population distribution, provided the population "
            "has finite variance. This permits statistical hypothesis testing (Z-tests, t-tests) and confidence intervals on real-world non-normal data."
        ),
    ),
    CuratedQuestion(
        topic="Statistics",
        difficulty="Medium",
        question="What is the exact definition of a p-value in hypothesis testing, and what common misconception must be avoided?",
        reference_answer=(
            "A p-value is the probability of observing a test statistic at least as extreme as the observed result, assuming the null hypothesis "
            "is true. The most common misconception is believing the p-value is 'the probability that the null hypothesis is true' or 'the "
            "probability the observed effect is due to random chance'. It is purely a conditional probability P(Data >= observed | H0 is true)."
        ),
    ),
    CuratedQuestion(
        topic="Statistics",
        difficulty="Hard",
        question="Explain Simpson's Paradox with an intuitive example, and how should a Data Scientist avoid falling into it during analysis?",
        reference_answer=(
            "Simpson's Paradox occurs when a statistical trend or correlation observed across different sub-groups reverses or disappears when "
            "the groups are aggregated. For example, Treatment A may have higher recovery rates than Treatment B in both mild and severe patient "
            "subgroups, but lower overall if Treatment A was disproportionately given to severe cases (confounding variable). To prevent this, "
            "data scientists must identify confounding variables, stratify analyses, and utilize causal DAGs or controlled matching."
        ),
    ),
]


def is_topic_compatible(bank_topic: str, requested_topic: str) -> bool:
    """Determine whether a curated question bank topic matches a user's requested topic."""
    b = bank_topic.strip().lower()
    r = requested_topic.strip().lower()

    if b == r:
        return True

    domains = {
        "sql": [
            "sql", "database", "databases", "postgres", "postgresql",
            "mysql", "sqlite", "rdbms", "relational", "query", "queries"
        ],
        "python": [
            "python", "python3", "programming", "scripting", "oop"
        ],
        "machine learning": [
            "machine learning", "ml", "statistical learning", "supervised",
            "unsupervised", "clustering", "regression", "classification"
        ],
        "deep learning & genai": [
            "deep learning", "genai", "generative ai", "neural",
            "transformer", "transformers", "llm", "rag", "lora", "attention"
        ],
        "statistics": [
            "statistics", "probability", "stats", "hypothesis testing",
            "p-value", "inferential"
        ],
    }

    # Ensure pure SQL requests never match ML, DL, Python, or Statistics
    is_pure_sql_req = any(term in r for term in domains["sql"]) and not any(
        term in r for term in domains["machine learning"] + domains["deep learning & genai"]
    )
    if is_pure_sql_req:
        return b == "sql"

    # Ensure pure Python requests never match SQL or Stats
    is_pure_python_req = any(term in r for term in domains["python"]) and not any(
        term in r for term in domains["sql"] + domains["machine learning"]
    )
    if is_pure_python_req:
        return b == "python"

    # General domain lookup
    target_domain = None
    for dom_name in domains:
        if b == dom_name:
            target_domain = dom_name
            break

    if target_domain and target_domain in domains:
        keywords = domains[target_domain]
        r_words = set(re.findall(r"\w+", r))
        if any(kw in r for kw in keywords) or any(kw in r_words for kw in keywords):
            return True

    return False


class QuestionRetriever:
    """TF-IDF and Cosine Similarity retrieval engine for interview questions."""

    def __init__(self, question_bank: list[CuratedQuestion] = CURATED_QUESTION_BANK):
        self.question_bank = list(question_bank)
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
        )
        self._corpus_texts = [
            f"{q.topic} {q.difficulty} {q.question}" for q in self.question_bank
        ]
        if self._corpus_texts:
            self._tfidf_matrix = self.vectorizer.fit_transform(self._corpus_texts)
        else:
            self._tfidf_matrix = None

    def retrieve_question(
        self,
        topic: str,
        difficulty: str,
        exclude_hashes: Optional[set[str]] = None,
        similarity_threshold: float = 0.20,
        focus_terms: Optional[list[str]] = None,
    ) -> Optional[dict[str, str]]:
        """Find the most relevant pre-generated question for topic and difficulty.

        Uses TF-IDF representation and cosine similarity. Can be biased toward
        personalized candidate growth/weakness areas using focus_terms, strictly
        filtered to topic-compatible candidates.
        """
        from backend.api.assessments import question_hash

        exclude_hashes = exclude_hashes or set()
        clean_topic = topic.strip().lower()
        clean_difficulty = difficulty.strip().capitalize()

        # 1. Filter candidates by matching difficulty AND topic compatibility
        matching_indices = [
            idx
            for idx, q in enumerate(self.question_bank)
            if q.difficulty.lower() == clean_difficulty.lower()
            and is_topic_compatible(q.topic, clean_topic)
        ]

        if not matching_indices or self._tfidf_matrix is None:
            return None

        # 2. Build query representation with optional focus terms
        if focus_terms:
            clean_focus = " ".join(f.strip().lower() for f in focus_terms if f.strip())
            query_text = f"{clean_topic} {clean_focus} {clean_difficulty}"
        else:
            query_text = f"{clean_topic} {clean_difficulty}"

        try:
            query_vec = self.vectorizer.transform([query_text])
        except Exception:
            return None

        # 3. Compute cosine similarity against candidates
        candidate_matrix = self._tfidf_matrix[matching_indices]
        similarities = cosine_similarity(query_vec, candidate_matrix).flatten()

        # 4. Rank candidates by similarity score descending
        sorted_candidate_indices = np.argsort(-similarities)

        for candidate_rank in sorted_candidate_indices:
            score = float(similarities[candidate_rank])
            original_idx = matching_indices[candidate_rank]
            candidate = self.question_bank[original_idx]

            # Calculate hash to verify user has not seen it yet
            candidate_hash = question_hash(candidate.question)
            if candidate_hash in exclude_hashes:
                continue

            # Check threshold
            if score >= similarity_threshold:
                return {
                    "question": candidate.question,
                    "reference_answer": candidate.reference_answer,
                    "retrieved": True,
                    "similarity_score": round(score, 3),
                }

        return None


# Global singleton retriever instance
retriever = QuestionRetriever()
