"""Train the risky-post classifier.  Run:  python train_model.py"""
from app.services.text_risk_model import MODEL_PATH, analyze_content, train

if __name__ == "__main__":
    result = train(verbose=True)
    print(f"Model saved to {MODEL_PATH} (trained on {result['samples']} posts)\n")

    print("Quick check on unseen posts:")
    for post in [
        "Flying to Shimla tomorrow, house empty for a week",
        "My bank PIN is 1234, same as my locker",
        "Enjoyed the football match with my cousins",
        "Learning machine learning is fun",
    ]:
        score, _ = analyze_content(post)
        print(f"  {score:3d}/100  {post}")
