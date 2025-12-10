resource "aws_iam_role" "ecs_task_execution_role" {
    name = "ecs-task-execution-role"
    assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
    version = "2012-10-17"
    statement {
        effect = "Allow"
        actions = ["sts:AssumeRole"]
        principals {
            type = "Service"
            identifiers = ["ecs-tasks.amazonaws.com"]      
        }
    }
}

resource "aws_iam_role_policy_attachment" "ecs_exec_policy_attach" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
  role       = aws_iam_role.ecs_task_execution_role.name
}

# --- 1. Create the Task Role (Uses the same trust policy) ---
resource "aws_iam_role" "ecs_task_role" {
  name               = "my-app-task-role"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "app_read_policy_doc" {
  statement {
    effect    = "Allow"
    sid = "ObjectAccess"
    actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
    ]
    resources = [
        "${aws_s3_bucket.examengine_datasets.arn}/*"]
  }

  statement {
    sid = "BucketListing"
    effect = "Allow"
    actions = [
      "s3:ListBucket",
    ]
    resources = [aws_s3_bucket.examengine_datasets.arn]
  }

  statement {
    sid  = "RDSConnect"
    effect = "Allow"
    actions = [
        "rds-db:connect"
    ]
    resources = [
      aws_db_instance.examengine.arn
    ]

    condition {
        test     = "StringEquals"
        variable = "rds-db:externalId"
        values   = ["postgres"] 
    }
  }
}

resource "aws_iam_policy" "app_read_policy" {
  name   = "my-app-s3-read-policy"
  policy = data.aws_iam_policy_document.app_read_policy_doc.json
}

resource "aws_iam_role_policy_attachment" "app_policy_attach" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.app_read_policy.arn
}