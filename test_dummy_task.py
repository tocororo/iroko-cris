#!/usr/bin/env python3
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from iroko.crawler.manager import crawler_manager
from iroko.crawler.schemas import CrawlerTaskConfig
from iroko.crawler.tasks.dummy_task import DummyTask

# Setup logging to see the output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

async def test_dummy_task():
    """Test the dummy task"""
    print("🧪 Testing Dummy Task...")
    
    # Manually register the task type first
    crawler_manager.register_task_type("DummyTask", DummyTask)
    
    # Create task configuration
    task_config = CrawlerTaskConfig(
        task_id="hello_world",
        name="Hello World Task",
        description="A simple task that prints hello messages to logs",
        config={
            "message": "Hello from config!",
            "iterations": 3
        },
        max_execution_time=10  # 10 seconds timeout
    )
    
    # Add task to manager
    await crawler_manager.add_task(task_config, "DummyTask")
    print("✅ Dummy task added to manager")
    
    # Execute the task
    execution = await crawler_manager.execute_task("hello_world")
    print(f"✅ Task execution started: {execution.execution_id}")
    
    # Monitor the task
    print("📊 Monitoring task execution...")
    while True:
        status = crawler_manager.get_task_status("hello_world")
        if not status:
            print("❌ Task status not found")
            break
            
        print(f"Status: {status.status}")
        
        if status.status in ["completed", "failed", "cancelled"]:
            if status.status == "completed":
                print("🎉 Task completed successfully!")
                print(f"Results: {status.results}")
            elif status.status == "failed":
                print(f"❌ Task failed: {status.error_message}")
            
            # Show execution log
            print("\nExecution Log:")
            for log_entry in status.execution_log:
                print(f"  - {log_entry}")
            break
        
        await asyncio.sleep(1)

async def test_multiple_dummies():
    """Test multiple dummy tasks"""
    print("\n🧪 Testing Multiple Dummy Tasks...")
    
    crawler_manager.register_task_type("DummyTask", DummyTask)
    
    # Create multiple dummy tasks
    tasks_configs = [
        CrawlerTaskConfig(
            task_id=f"dummy_{i}",
            name=f"Dummy Task {i}",
            description=f"Test dummy task #{i}",
            config={"iteration": i},
            max_execution_time=5
        ) for i in range(3)
    ]
    
    # Add all tasks
    for config in tasks_configs:
        await crawler_manager.add_task(config, "DummyTask")
        print(f"✅ Added task: {config.task_id}")
    
    # Execute them sequentially
    for config in tasks_configs:
        execution = await crawler_manager.execute_task(config.task_id)
        print(f"🚀 Started: {config.task_id} - {execution.execution_id}")
        
        # Wait for completion
        while True:
            status = crawler_manager.get_task_status(config.task_id)
            if status and status.status in ["completed", "failed", "cancelled"]:
                print(f"✅ {config.task_id} finished: {status.status}")
                break
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    print("🚀 Starting Dummy Task Tests")
    
    # Test single task
    asyncio.run(test_dummy_task())
    
    # Test multiple tasks
    asyncio.run(test_multiple_dummies())
    
    print("🎊 All tests completed!")