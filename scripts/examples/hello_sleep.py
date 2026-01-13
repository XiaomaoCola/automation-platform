import time

def main(seconds: int = 5):
    print(f"start, sleep {seconds}s")
    time.sleep(seconds)
    print("done")

if __name__ == "__main__":
    main()
