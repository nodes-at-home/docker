FROM python:3.8-slim-buster

# Set the working directory to /app
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the current directory contents into the container at /app
# python script is mapped by volume option in docker compose, because of (non) visibility for environment variables
#COPY ./fritzinfluxdb.* /app

# run daemon
CMD [ "python", "./fritzinfluxdb.py" ]
