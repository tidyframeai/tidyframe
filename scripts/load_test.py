#!/usr/bin/env python3
"""
TidyFrame Load Testing Script
Tests concurrent file uploads to verify system performance
"""

import asyncio
import aiohttp
import time
import json
from pathlib import Path
import argparse
from typing import List, Dict
import statistics


class LoadTester:
    def __init__(self, base_url: str, num_concurrent: int = 5):
        self.base_url = base_url.rstrip('/')
        self.num_concurrent = num_concurrent
        self.results: List[Dict] = []

    def create_test_csv(self, size: str = "small") -> str:
        """Create a test CSV file with sample names"""
        names = [
            "John Smith", "Jane Doe", "Michael Johnson", "Sarah Williams",
            "Robert Brown", "Emily Davis", "David Miller", "Jennifer Wilson",
            "James Moore", "Mary Taylor", "Christopher Anderson", "Patricia Thomas"
        ]

        if size == "small":
            data = names[:5]
        elif size == "medium":
            data = names * 10  # 120 names
        else:  # large
            data = names * 100  # 1200 names

        csv_content = "names\n" + "\n".join(data)

        # Write to temp file
        filepath = f"/tmp/load_test_{size}.csv"
        with open(filepath, 'w') as f:
            f.write(csv_content)

        return filepath

    async def upload_file(self, session: aiohttp.ClientSession, filepath: str,
                         test_num: int) -> Dict:
        """Upload a single file and measure performance"""
        start_time = time.time()

        try:
            # Read file
            with open(filepath, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file',
                              f,
                              filename=f'test_{test_num}.csv',
                              content_type='text/csv')

                # Upload
                async with session.post(f'{self.base_url}/api/upload',
                                       data=data,
                                       timeout=aiohttp.ClientTimeout(total=120)) as response:
                    duration = time.time() - start_time
                    status = response.status

                    try:
                        result = await response.json()
                    except:
                        result = {'error': 'Invalid JSON response'}

                    return {
                        'test_num': test_num,
                        'status': status,
                        'duration': duration,
                        'success': status == 200,
                        'job_id': result.get('job_id') if status == 200 else None,
                        'error': result.get('message') if status != 200 else None
                    }
        except Exception as e:
            duration = time.time() - start_time
            return {
                'test_num': test_num,
                'status': 0,
                'duration': duration,
                'success': False,
                'error': str(e)
            }

    async def wait_for_job(self, session: aiohttp.ClientSession, job_id: str) -> Dict:
        """Poll job status until completion"""
        start_time = time.time()
        max_wait = 300  # 5 minutes max

        while time.time() - start_time < max_wait:
            try:
                async with session.get(f'{self.base_url}/api/jobs/{job_id}',
                                      timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        status = result.get('status')

                        if status in ['completed', 'failed']:
                            return {
                                'job_id': job_id,
                                'status': status,
                                'duration': time.time() - start_time,
                                'processed_rows': result.get('processed_rows', 0),
                                'successful_parses': result.get('successful_parses', 0)
                            }
            except Exception as e:
                print(f"Error checking job {job_id}: {e}")

            await asyncio.sleep(2)

        return {
            'job_id': job_id,
            'status': 'timeout',
            'duration': time.time() - start_time
        }

    async def run_upload_test(self, file_size: str = "small"):
        """Run concurrent upload test"""
        print(f"\n{'='*80}")
        print(f"Running {self.num_concurrent} concurrent uploads ({file_size} files)...")
        print(f"{'='*80}\n")

        # Create test file
        filepath = self.create_test_csv(file_size)

        # Create session
        async with aiohttp.ClientSession() as session:
            # Launch concurrent uploads
            tasks = [
                self.upload_file(session, filepath, i)
                for i in range(self.num_concurrent)
            ]

            start_time = time.time()
            results = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time

            # Analyze results
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]

            print(f"\nUpload Results:")
            print(f"  Total Requests: {len(results)}")
            print(f"  Successful: {len(successful)}")
            print(f"  Failed: {len(failed)}")
            print(f"  Total Time: {total_duration:.2f}s")
            print(f"  Avg Response Time: {statistics.mean([r['duration'] for r in results]):.2f}s")

            if successful:
                print(f"  Min Response Time: {min(r['duration'] for r in successful):.2f}s")
                print(f"  Max Response Time: {max(r['duration'] for r in successful):.2f}s")

            # Show failures
            if failed:
                print(f"\n❌ Failed Requests:")
                for r in failed:
                    print(f"  Test #{r['test_num']}: {r.get('error', 'Unknown error')}")

            # Wait for job completion
            if successful:
                print(f"\nWaiting for jobs to complete...")
                job_tasks = [
                    self.wait_for_job(session, r['job_id'])
                    for r in successful if r.get('job_id')
                ]

                job_results = await asyncio.gather(*job_tasks)

                completed_jobs = [j for j in job_results if j['status'] == 'completed']
                print(f"\n  Completed Jobs: {len(completed_jobs)}/{len(job_results)}")

                if completed_jobs:
                    avg_processing = statistics.mean([j['duration'] for j in completed_jobs])
                    print(f"  Avg Processing Time: {avg_processing:.2f}s")

            return results

    async def run_all_tests(self):
        """Run comprehensive load tests"""
        print("=" * 80)
        print("TIDYFRAME LOAD TESTING")
        print("=" * 80)

        # Test 1: Small files
        await self.run_upload_test("small")
        await asyncio.sleep(2)

        # Test 2: Medium files
        if self.num_concurrent <= 10:
            await self.run_upload_test("medium")
            await asyncio.sleep(2)

        print(f"\n{'='*80}")
        print("LOAD TESTING COMPLETE")
        print(f"{'='*80}\n")


async def main():
    parser = argparse.ArgumentParser(description="TidyFrame Load Testing")
    parser.add_argument('--url', default='https://tidyframe.com',
                       help='Base URL (default: https://tidyframe.com)')
    parser.add_argument('--concurrent', type=int, default=5,
                       help='Number of concurrent requests (default: 5)')
    parser.add_argument('--size', choices=['small', 'medium', 'large'], default='small',
                       help='File size to test (default: small)')

    args = parser.parse_args()

    tester = LoadTester(args.url, args.concurrent)

    if args.size:
        await tester.run_upload_test(args.size)
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
