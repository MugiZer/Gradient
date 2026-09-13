import argparse

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run the Gradient backend")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    uvicorn.run("gradient.api.app:create_app", factory=True, host="127.0.0.1", port=args.port,
                proxy_headers=False)


if __name__ == "__main__":
    main()
