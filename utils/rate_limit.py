from langchain_core.rate_limiters import InMemoryRateLimiter

rate_limiter = InMemoryRateLimiter(
    requests_per_second= 1,  
    check_every_n_seconds=0.1,  
    max_bucket_size=10,  
)