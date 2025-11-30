resource "aws_ecs_cluster" "cluster" {
    name = "ee-cluster"
}

resource "aws_ecs_task_definition" "frontend-task" {
    family = "ee-tasks"
    requires_compatabilities = ["FARGATE"]

}