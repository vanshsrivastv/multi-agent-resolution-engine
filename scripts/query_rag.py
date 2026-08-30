import sys

from app.rag.search import search


def main():
    query = " ".join(sys.argv[1:]) or "my password reset email never arrives"
    print(f"Query: {query}\n")
    for r in search(query):
        print(f"[{r['score']:.3f}] {r['source']}")
        print(r["text"].strip().splitlines()[0])
        print("---")


if __name__ == "__main__":
    main()
