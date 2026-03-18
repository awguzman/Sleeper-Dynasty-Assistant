# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set a default port for local testing.
# Google Cloud Run will override this environment variable at runtime.
ENV PORT 8080

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Document the port that may need publishing.
EXPOSE 8080

# Run the web service on container startup.
# --timeout 0: Disables gunicorn's internal timeout, letting Cloud Run handle it.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 dashboard:server
