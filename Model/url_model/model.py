from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class URLModel:
    def __init__(self):
        self.model_name = "ealvaradob/bert-finetuned-phishing"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)


    def check_url(self, url):
        inputs = self.tokenizer(url, return_tensors="pt", truncation=True, padding=True, max_length=128)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
        
        phishing_score = probabilities[0][1].item() # Index 1 is Phishing
        return phishing_score


    def test_model(self, urls):
        scores = {}
        for url in urls:
            score = self.check_url(url)
            scores[url] = score
        return scores