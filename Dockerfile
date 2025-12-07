FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY config.py .
COPY utils.py .
COPY handler.py .
COPY clients/ ./clients/
COPY models/ ./models/
COPY services/ ./services/
COPY prompts/ ./prompts/

# Lambda handler
CMD ["handler.lambda_handler"]
