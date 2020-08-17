# Set up the basics
FROM python:3.8-slim AS base-stage
RUN apt-get update && apt-get install -y openssh-client openssl telnet && rm -rf /var/lib/apt/lists/*

# now do everything as a non-privileged user
RUN adduser toolop --gecos "" --disabled-password
RUN mkdir -p /home/toolop/app && chown -R toolop:toolop /home/toolop
USER toolop
WORKDIR /home/toolop

# use a venv
COPY ./requirements.txt .
RUN python3 -m venv venv
ENV PATH="/home/toolop/venv/bin:$PATH"
RUN pip install -r requirements.txt


# run tests with tox
FROM base-stage AS test-stage
RUN pip install tox
WORKDIR /home/toolop/app
COPY . .
RUN tox


# discard the test stage and actually run in production
FROM base-stage AS deploy-stage

WORKDIR /home/toolop/app
COPY --from=test-stage /home/toolop/app/pbxd ./pbxd

# open the container port where the flask app listens
EXPOSE 8000

# start the executable
ENTRYPOINT ["gunicorn",  "pbxd.app:load()"]

# default parameters that can be overridden with: docker run <image> new params
CMD ["-b", ":8000", "--access-logfile", "-", "--log-level", "INFO"]
