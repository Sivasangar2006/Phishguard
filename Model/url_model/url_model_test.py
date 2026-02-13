from model import URLModel

model = URLModel()
scores = model.test_model(urls = [
            "http://www.dfghjlkkjhgf6798hhyg.com",
            "http://www.appspot.com/"
        ])

print(scores)
