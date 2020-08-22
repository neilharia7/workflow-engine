pipeline {
	agent any

	environment {
		ECR = "740186269845.dkr.ecr.ap-south-1.amazonaws.com/flowxpert-engine"
		BUILD_IMAGE = "backend:latest"
		LATEST_IMAGE = "${env.ECR}:latest"
	}

	// Let the adventure begin..
	stages {

		// Extract the git tag from the commit id
		stage ("Advent") {
			steps {
				script {
					env.COMMIT_ID = sh(returnStdout: true, script: "git rev-list --tags --date-order | head -1").trim()
					echo "${env.COMMIT_ID}"
					env.BUILD_VERSION = sh(returnStdout: true, script: "git show-ref --tags | grep ${env.COMMIT_ID} | awk -F'[/*]' '{print \$3}'").trim()
					echo "${env.BUILD_VERSION}"

					env.TAGGED_IMAGE = "${env.ECR}:${env.BUILD_VERSION}"
				}
			}

			post {
				failure {
					error "Error fetching credentials, inevitable death of pipeline, adios .."
				}
			}
		}

		stage ("Awakening") {
			when {
				expression { env.BUILD_VERSION != null }
			}

			steps {
				script {
					docker.build("$BUILD_IMAGE")

					// fetch aws login credentials
					sh '$(aws ecr get-login --no-include-email --region ap-south-1)'
				}
			}

			post {
				failure {
					error "Error building docker image, adios .. "
				}
			}
		}

		stage("Discovery") {
			steps {

				script {
					sh """docker tag ${env.BUILD_IMAGE} ${env.LATEST_IMAGE}
                       	docker tag ${env.BUILD_IMAGE} ${env.TAGGED_IMAGE}
                        docker push ${env.LATEST_IMAGE}
                        docker push ${env.TAGGED_IMAGE}"""
				}
			}

			post {
				success {
					sh "docker rmi ${env.LATEST_IMAGE} ${env.TAGGED_IMAGE}"
				}
			}
		}

		stage ("Life Purpose") {
			steps {
				sh "chmod +x changeVersionTag.sh"
				sh "./changeVersionTag ${env.BUILD_VERSION}"

				sshagent(['Neil-Airlflow']) {
    				// some block
    				sh "scp -o StrictHostKeyChecking=no k8s.yaml ec2-user@13.233.114.63:/home/ec2-user/"

    				script {
    					try {
    						sh "ssh ec2-user@13.233.114.63 kubectl apply -f ."
    					} catch (err){
    					    echo err.getMessage()
    						sh "ssh ec2-user@13.233.114.63 kubectl create -f ."
    					}
    				}
				}
			}
		}
	}
}