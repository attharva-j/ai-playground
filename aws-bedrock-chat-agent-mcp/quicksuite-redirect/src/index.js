function handler(event) {
    var host = event.request.headers.host ? event.request.headers.host.value : '';

    var path_host_map = {
        'chat-np.<your-domain.com>': 'ai-foundation-nonprod/<nonprod-instance-id>',
        'chat.<your-domain.com>': 'ai-foundation-prod/<prod-instance-id>'
    };

    if (path_host_map[host]) {
        return {
            statusCode: 302,
            statusDescription: 'Found',
            headers: {
                'location': { value: `https://<your-org>.awsapps.com/start/#/saml/default/${path_host_map[host]}` }
            }
        };
    }

    return {
        statusCode: 400,
        statusDescription: 'Bad Request'
    };
}
