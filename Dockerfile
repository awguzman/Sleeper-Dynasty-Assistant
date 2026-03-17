# Use an official lightweight Python image.
FROM python:3.13-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install production dependencies.
# Upgrade pip to ensure latest wheel support
RUN pip install --no-cache-dir --upgrade pip
# Install app dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
# --timeout 0: Disables gunicorn's internal timeout, letting Cloud Run handle it.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 dashboard:server
