from gensim import corpora, models
import re

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[0-9A-Za-z가-힣]+", (text or "").lower())

class TinyLDAModel:
    def __init__(self, num_topics: int = 5):
        self.num_topics = num_topics
        self.dictionary = None
        self.lda = None

    def fit(self, docs: list[str]):
        tokens_list = [_tokenize(d) for d in docs if d]
        if not tokens_list:
            return
        self.dictionary = corpora.Dictionary(tokens_list)
        bows = [self.dictionary.doc2bow(t) for t in tokens_list]
        # 소형 LDA (패스/반복 최소화)
        self.lda = models.LdaModel(
            corpus=bows,
            id2word=self.dictionary,
            num_topics=self.num_topics,
            iterations=50,
            passes=2,
            random_state=42,
        )

    def infer_topic(self, doc: str) -> int | None:
        if not self.lda or not self.dictionary:
            return None
        bow = self.dictionary.doc2bow(_tokenize(doc))
        dist = self.lda.get_document_topics(bow)
        if not dist: return None
        # 확률 최대의 토픽 id
        return max(dist, key=lambda x: x[1])[0]
