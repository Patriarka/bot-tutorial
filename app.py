import os
from flask import Flask, request
from github import Github, GithubIntegration, UnknownObjectException

'''
Autores: Alexandre Scrocaro, Jessé Pires, Jhonatan Cunha e Matheus Patriarca.
Código responsável por apresentar mensagens de agradecimentos quando o usuário faz um pull request, um merge e apagar a branch após o merge.
'''

app = Flask(__name__)

app_id = '<your_app_number_here>'

# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('bot_key.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()
    
# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def pr_opened_event(repo, payload):
    pr = repo.get_issue(number=payload['pull_request']['number'])
    author = pr.user.login

    is_first_pr = repo.get_issues(creator=author).totalCount

    if is_first_pr == 1:
        response = f"Thanks for opening this pull request, @{author}! " \
                   f"The repository maintainers will look into it ASAP! :speech_balloon:"
        pr.create_comment(f"{response}")
        pr.add_to_labels("needs review")

'''
 @params: repo: repositório a ser trabalhado, branch_name: nome da branch a ser excluída.
 A branch que tem o nome passado por parâmetro é excluída.
'''
def delete_branch_after_accepted_pr(repo, branch_name):
    try:
        branch = repo.get_git_ref("heads/%s" % branch_name)
        branch.delete()
    except UnknownObjectException:
        print('No such branch', branch_name)

'''
 @params: repo: repositório a ser trabalhado, payload: outros dados do github.
 Após o processo de merge, é apresentado uma mensagem ao usuário e a branch que foi feita o merge é excluída.
'''
def pr_closed_event(repo, payload):
    pr = repo.get_issue(number=payload['pull_request']['number'])
    author = pr.user.login

    if payload['pull_request']['merged']:
        response = f"Thanks, {author}! Your merge is completed :sunglasses:!"
        pr.create_comment(f"{response}")
        pr.add_to_labels("Congratulation")

        # Delete branch
        branch_name = payload['pull_request']['head']['ref']
        delete_branch_after_accepted_pr(repo, branch_name)

@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub pull request creation event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        pr_opened_event(repo, payload)
    elif all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':     # Check if the event is a Github merge, and was accepted
        pr_closed_event(repo, payload)

    return "", 204

if __name__ == "__main__":
    app.run(debug=True, port=5000)