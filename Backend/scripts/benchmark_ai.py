import time
import os
import statistics
import logging
from Backend.lead_magnets.perplexity_client import PerplexityClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def benchmark_ai_generation(iterations=3):
    """Benchmark AI content generation response times."""
    client = PerplexityClient()
    if not client.api_key:
        logger.error("❌ AI API key (GEMINI_API_KEY or PERPLEXITY_API_KEY) is missing. Skipping benchmark.")
        return

    logger.info(f"🚀 Starting AI generation benchmark ({iterations} iterations) via {client.provider}...")
    
    signals = {
        "main_topic": "Adaptive Reuse of Industrial Assets",
        "lead_magnet_type": "Strategic Guide",
        "target_audience": "Institutional Real Estate Funds",
        "audience_pain_points": "High acquisition costs, regulatory hurdles",
        "desired_outcome": "Unlock value in brownfield sites",
        "call_to_action": "Schedule a feasibility audit",
        "special_requests": "Focus on ROI optimization."
    }
    firm_profile = {
        "firm_name": "Adaptive Strategy Partners",
        "work_email": "partners@adaptivestrategy.com",
        "phone_number": "+1 555-123-4567",
        "firm_website": "www.adaptivestrategy.com",
        "primary_brand_color": "#2a5766",
        "secondary_brand_color": "#FFFFFF"
    }

    response_times = []
    success_count = 0
    failure_count = 0

    for i in range(iterations):
        if i > 0:
            delay = 15 # Wait 15s between iterations to respect rate limits
            logger.info(f"⏳ Waiting {delay}s before next iteration to respect rate limits...")
            time.sleep(delay)
            
        logger.info(f"📊 Iteration {i+1}/{iterations}...")
        start_time = time.time()
        try:
            ai_content = client.generate_lead_magnet_json(signals, firm_profile)
            duration = time.time() - start_time
            response_times.append(duration)
            success_count += 1
            logger.info(f"✅ Successful generation in {duration:.2f} seconds.")
        except Exception as e:
            failure_count += 1
            logger.error(f"❌ Generation failed: {str(e)}")

    if response_times:
        avg_time = statistics.mean(response_times)
        max_time = max(response_times)
        min_time = min(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        logger.info("\n" + "="*50)
        logger.info(f"📊 AI BENCHMARK RESULTS ({client.provider})")
        logger.info("="*50)
        logger.info(f"✅ Total Successes: {success_count}/{iterations}")
        logger.info(f"❌ Total Failures:  {failure_count}/{iterations}")
        logger.info(f"⏱️  Average Time:    {avg_time:.2f} seconds")
        logger.info(f"⏱️  Minimum Time:    {min_time:.2f} seconds")
        logger.info(f"⏱️  Maximum Time:    {max_time:.2f} seconds")
        logger.info(f"📉 Std Deviation:   {std_dev:.2f} seconds")
        logger.info("="*50)
        
        # Threshold checks
        if avg_time > 60:
            logger.warning("⚠️  Average response time is over 60 seconds. Consider optimization or model switching.")
        else:
            logger.info("✅ Performance is within acceptable thresholds (< 60s).")
    else:
        logger.error("❌ Benchmark failed to collect any successful results.")

if __name__ == '__main__':
    # Default to 2 iterations for quick check
    benchmark_ai_generation(iterations=2)
