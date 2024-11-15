import pytest
import time
import asyncio
import aiohttp
import statistics
from typing import List, Dict, Any
from fastapi.testclient import TestClient

async def send_concurrent_requests(
    test_client: TestClient,
    endpoint: str,
    payload: Dict[str, Any],
    num_requests: int
) -> List[float]:
    """Send concurrent requests and measure response times"""
    async with aiohttp.ClientSession() as session:
        tasks = []
        for _ in range(num_requests):
            tasks.append(
                asyncio.create_task(
                    session.post(
                        f"http://testserver{endpoint}",
                        json=payload
                    )
                )
            )
        
        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        response_times = []
        for response in responses:
            assert response.status == 200
            response_times.append(response.elapsed.total_seconds())
        
        return response_times

def test_validation_performance(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test validation endpoint performance under load"""
    num_requests = 100
    response_times = asyncio.run(
        send_concurrent_requests(
            test_client,
            "/validate",
            test_admission_request,
            num_requests
        )
    )
    
    # Calculate statistics
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
    
    # Assert performance requirements
    assert avg_response_time < 0.1  # Average response time under 100ms
    assert p95_response_time < 0.2  # 95th percentile under 200ms
    assert p99_response_time < 0.5  # 99th percentile under 500ms

def test_mutation_performance(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test mutation endpoint performance under load"""
    num_requests = 100
    response_times = asyncio.run(
        send_concurrent_requests(
            test_client,
            "/mutate",
            test_admission_request,
            num_requests
        )
    )
    
    # Calculate statistics
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
    p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
    
    # Assert performance requirements
    assert avg_response_time < 0.1  # Average response time under 100ms
    assert p95_response_time < 0.2  # 95th percentile under 200ms
    assert p99_response_time < 0.5  # 99th percentile under 500ms

def test_memory_usage(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test memory usage under load"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Send requests
    num_requests = 1000
    asyncio.run(
        send_concurrent_requests(
            test_client,
            "/validate",
            test_admission_request,
            num_requests
        )
    )
    
    final_memory = process.memory_info().rss
    memory_increase = (final_memory - initial_memory) / 1024 / 1024  # Convert to MB
    
    # Assert memory usage
    assert memory_increase < 50  # Memory increase should be less than 50MB

def test_cpu_usage(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test CPU usage under load"""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_cpu_percent = process.cpu_percent()
    
    # Send requests
    num_requests = 1000
    asyncio.run(
        send_concurrent_requests(
            test_client,
            "/validate",
            test_admission_request,
            num_requests
        )
    )
    
    final_cpu_percent = process.cpu_percent()
    cpu_increase = final_cpu_percent - initial_cpu_percent
    
    # Assert CPU usage
    assert cpu_increase < 80  # CPU usage should not spike above 80%

def test_connection_handling(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test connection handling under high concurrency"""
    import socket
    
    # Create many connections
    sockets = []
    try:
        for _ in range(1000):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("localhost", 8080))
            sockets.append(sock)
    except Exception as e:
        # Clean up sockets
        for sock in sockets:
            sock.close()
        raise e
    
    # Send requests while holding connections
    num_requests = 100
    response_times = asyncio.run(
        send_concurrent_requests(
            test_client,
            "/validate",
            test_admission_request,
            num_requests
        )
    )
    
    # Clean up sockets
    for sock in sockets:
        sock.close()
    
    # Calculate statistics
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]
    
    # Assert performance under connection pressure
    assert avg_response_time < 0.2  # Average response time under 200ms
    assert p95_response_time < 0.5  # 95th percentile under 500ms

def test_request_timeout(test_client: TestClient, test_admission_request: Dict[str, Any]):
    """Test request timeout handling"""
    import asyncio
    
    async def send_slow_request():
        async with aiohttp.ClientSession() as session:
            # Add a delay parameter to simulate slow processing
            test_admission_request["delay"] = 5  # 5 second delay
            
            start_time = time.time()
            try:
                async with session.post(
                    "http://testserver/validate",
                    json=test_admission_request,
                    timeout=2  # 2 second timeout
                ) as response:
                    await response.text()
            except asyncio.TimeoutError:
                end_time = time.time()
                return end_time - start_time
    
    timeout_duration = asyncio.run(send_slow_request())
    
    # Assert timeout occurred around 2 seconds
    assert 1.9 <= timeout_duration <= 2.1

def test_error_response_performance(test_client: TestClient):
    """Test error response performance"""
    num_requests = 100
    invalid_request = {"invalid": "request"}
    
    response_times = asyncio.run(
        send_concurrent_requests(
            test_client,
            "/validate",
            invalid_request,
            num_requests
        )
    )
    
    # Calculate statistics
    avg_response_time = statistics.mean(response_times)
    p95_response_time = statistics.quantiles(response_times, n=20)[18]
    
    # Assert error response performance
    assert avg_response_time < 0.05  # Average error response time under 50ms
    assert p95_response_time < 0.1  # 95th percentile under 100ms
