resource "aws_iam_role" "ecs_task_execution_role" {
    name = "ecs-task-execution-role"
    assume_role_policy = "data.aws_iam_policy_document.ecs_task_assume_role.json"
}

data "aws_iam_policy_document" "ecs_task_assume_role" {
    version = "2012-10-17"
    statemnent: [
        effect = "Alllow",
        actions = ["sts:AssumeRole"]
        principals {
            type = "Service"
            "Service": "ecs-tasks.amazonaws.com"
        },
    ]
}