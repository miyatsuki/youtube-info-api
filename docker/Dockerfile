# gitからのpip install用
FROM python:3.12 AS tools
ENV COMMIT_HASH 231bc8eef59aa40e74deadc05aeeb9b30836ac8e
RUN wget https://github.com/miyatsuki/tools/archive/${COMMIT_HASH}.zip -O main.zip
RUN unzip main.zip
RUN mv tools-${COMMIT_HASH} tools-main

# 本番用
FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY --from=tools /tools-main /tmp/tools-main
RUN pip install /tmp/tools-main --target "${LAMBDA_TASK_ROOT}"
COPY app.py ${LAMBDA_TASK_ROOT}
CMD [ "app.lambda_handler" ]
