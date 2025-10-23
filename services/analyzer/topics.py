import re
from typing import List, Optional
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

def _tokenize(text: str) -> List[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", (text or "").lower())

_TOKEN_PATTERN = r"[0-9A-Za-z가-힣]+"

class TinyLDAModel:
    def __init__(self, num_topics: int = 5, max_features: int = 5000):
        self.num_topics = num_topics
        self.max_features = max_features
        self.vectorizer: Optional[CountVectorizer] = None
        self.lda: Optional[LatentDirichletAllocation] = None

    def fit(self, docs: List[str]):
        corpus = [d for d in docs if d]
        if not corpus:
            return
        # 토큰 패턴을 한/영 공용으로
        self.vectorizer = CountVectorizer(
            token_pattern=_TOKEN_PATTERN,
            max_features=self.max_features,
            min_df=2
        )
        X = self.vectorizer.fit_transform(corpus)
        self.lda = LatentDirichletAllocation(
            n_components=self.num_topics,
            learning_method="batch",
            max_iter=30,
            random_state=42,
            evaluate_every=0,
        )
        self.lda.fit(X)

    def infer_topic(self, doc: str) -> Optional[int]:
        if not self.lda or not self.vectorizer or not doc:
            return None
        X = self.vectorizer.transform([doc])
        # transform은 문서의 토픽 분포(확률) 반환
        dist = self.lda.transform(X)  # shape: (1, n_topics)
        if dist is None or dist.shape[0] == 0:
            return None
        return int(dist[0].argmax())
