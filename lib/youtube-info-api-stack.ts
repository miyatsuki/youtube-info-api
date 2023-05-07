import * as cdk from 'aws-cdk-lib';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { HttpMethod, FunctionUrlAuthType } from "aws-cdk-lib/aws-lambda";
import { Construct } from 'constructs';
import * as dotenv from 'dotenv';

dotenv.config();

export class YoutubeInfoApiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // The code that defines your stack goes here

    // ECR関連
    const lamdaRepository = new ecr.Repository(this, 'lambda');

    // Lambda関連
    const lambdaFunction = new lambda.Function(this, 'apiFunction', {
      code: lambda.Code.fromEcrImage(lamdaRepository, {
        cmd: ["app.lambda_handler"],
        tagOrDigest: "latest"
      }),
      runtime: lambda.Runtime.FROM_IMAGE,
      handler: lambda.Handler.FROM_IMAGE,
      timeout: cdk.Duration.seconds(60 * 15),
      environment: {
        OPENAI_API_KEY: process.env.OPENAI_API_KEY!,
        YOUTUBE_DATA_API_TOKEN: process.env.YOUTUBE_DATA_API_TOKEN!,
      }
    });

    const lambdaFunctionURL = lambdaFunction.addFunctionUrl({
      authType: FunctionUrlAuthType.NONE,
      cors: {
        allowedMethods: [HttpMethod.ALL],
        allowedOrigins: ["*"],
      },
    });

    // example resource
    // const queue = new sqs.Queue(this, 'YoutubeInfoApiQueue', {
    //   visibilityTimeout: cdk.Duration.seconds(300)
    // });
  }
}
