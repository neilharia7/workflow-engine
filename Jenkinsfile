pipeline {
    agent any

    environment {
        VERSION = sh(returnStdout: true,script: 'git tag --contains').trim()
        IMAGE = "airflow:latest"
        ECR = "740186269845.dkr.ecr.ap-south-1.amazonaws.com/flowxpert-engine"
    }

    stages {

        stage("Building Image") {
            steps {
                script {
                    docker.build("$IMAGE")
                }
            }
        }

        stage("Get Docker Creds") {
            steps {
                script {
					sh '$(aws ecr get-login --no-include-email --region ap-south-1)'
				}
            }
        }

        stage("Push Image to ECR") {
            steps {
	            script {
						sh """docker tag $IMAGE $ECR:$VERSION
							docker tag $IMAGE $ECR:latest
							docker push $ECR:latest
							docker push $ECR:$VERSION"""
					}
			}

        }
    }

    // remove docker images to save space
	post {
		always {
			sh "docker rmi $IMAGE $ECR:latest $ECR:$VERSION | true"
		}
	}
}