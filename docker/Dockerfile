# gitからのpip install用
FROM python:3.10 as tools
RUN wget https://github.com/miyatsuki/tools/archive/refs/heads/main.zip
RUN unzip main.zip

# 本番用
FROM public.ecr.aws/lambda/python:3.10
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY --from=tools /tools-main /tmp/tools-main
RUN pip install /tmp/tools-main --target "${LAMBDA_TASK_ROOT}"
COPY app.py ${LAMBDA_TASK_ROOT}
CMD [ "app.lambda_handler" ]
