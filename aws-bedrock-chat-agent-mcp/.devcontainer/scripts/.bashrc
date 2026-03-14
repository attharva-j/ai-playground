elevate-role() {
    if [ -z "$AWS_ACCESS_KEY_ID" ] && aws sts get-caller-identity --profile sso >/dev/null 2>&1; then
        export AWS_PROFILE=sso
    else
        aws configure --profile sso set aws_access_key_id $AWS_ACCESS_KEY_ID
        aws configure --profile sso set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
        aws configure --profile sso set aws_session_token $AWS_SESSION_TOKEN
    fi
    credentials=$(aws sts assume-role \
        --role-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/enterprise/pam/$1 \
        --role-session-name $(aws sts get-caller-identity --query UserId --output text | awk -F':' '{print $2}') \
        --query "Credentials.[AccessKeyId,SecretAccessKey,SessionToken]" \
        --output text)
    aws configure --profile $1 set aws_access_key_id $(echo $credentials | awk '{print $1}')
    aws configure --profile $1 set aws_secret_access_key $(echo $credentials | awk '{print $2}')
    aws configure --profile $1 set aws_session_token $(echo $credentials | awk '{print $3}')
    export AWS_PROFILE=$1
    unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
}

ecr-helm-login() {
    region=$1
    account=$2

    if [ -z "$account" ]; then
        account=$(aws sts get-caller-identity --query Account --output text)
    fi

    ECR_REGISTRY_URL=$account.dkr.ecr.$region.amazonaws.com
    ECR_TOKEN=$(aws ecr get-authorization-token --registry-ids $account --region $region --query authorizationData[0].authorizationToken --output text)

    HELM_REGISTRY_CONFIG=${HELM_REGISTRY_CONFIG:-~/.config/helm/registry/config.json}

    if [ ! -f "$HELM_REGISTRY_CONFIG" ]; then
        mkdir -p "$(dirname "$HELM_REGISTRY_CONFIG")"
        echo "{}" > "$HELM_REGISTRY_CONFIG"
    fi

    jq --arg url "$ECR_REGISTRY_URL" --arg token "$ECR_TOKEN" \
        '.auths[$url] = { "auth": $token }' "$HELM_REGISTRY_CONFIG" > "${HELM_REGISTRY_CONFIG}.tmp"
    mv "${HELM_REGISTRY_CONFIG}.tmp" "$HELM_REGISTRY_CONFIG"
}
