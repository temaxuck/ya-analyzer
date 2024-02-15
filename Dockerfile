# ==================== Environment build image ====================
# Pull "heavy" image (~1GB, or ~500MB compressed) with dependencies
# necesarry for building modules
FROM snakepacker/python:all as builder

# Create virtual environment and update pip
RUN python3.10 -m venv /usr/share/python3/app
RUN /usr/share/python3/app/bin/pip install -U pip

# Installing dependencies separately
# This way dependencies are cached by pip and docker skips this step 
# if requirements.txt has not been changed
COPY requirements.txt /mnt/
RUN /usr/share/python3/app/bin/pip install -Ur /mnt/requirements.txt

# Copy source distribution and install it
COPY dist/ /mnt/dist/
RUN /usr/share/python3/app/bin/pip install /mnt/dist/* \
    && /usr/share/python3/app/bin/pip check

# ==================== Final image ====================
# Pull "light" image (~100MB, or ~50MB compressed) with python
FROM snakepacker/python:3.10 as api

# Copy from builder container python virtual environment
COPY --from=builder /usr/share/python3/app /usr/share/python3/app

# Set links to be able to use applicatoin's commands
RUN ln -snf /usr/share/python3/app/bin/analyzer-* /usr/local/bin

# Set a default command to run when the container has been installed
CMD ["analyzer-api", "--pg-url=postgresql://admin:admin@analyzer-postgres:5432/analyzer"]