# Cherenkov Dashboard Performance Report

## Methodology
The performance evaluation was conducted using `curl` via WSL to measure the total response time of the Cherenkov dashboard running locally.

Command executed:
`wsl curl -s -w "%{http_code} %{time_total}\n" -o /dev/null http://localhost:8000`

## Results
- **HTTP Status Code**: 200 OK
- **Total Response Time**: ~0.0036 seconds (3.6 milliseconds)

## Conclusion
The dashboard endpoint (`http://localhost:8000`) is highly responsive, serving requests in under 4 milliseconds with a successful 200 OK status code. This indicates excellent baseline performance for the local dashboard server.
