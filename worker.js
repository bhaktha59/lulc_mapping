export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Seamless reverse proxy for all API endpoints
    if (url.pathname.startsWith('/api/') || url.pathname === '/api') {
      const backendBase = env.BACKEND_API_URL || 'https://lulc-mapping-api.onrender.com';
      const targetUrl = new URL(url.pathname + url.search, backendBase);
      const forwardHeaders = new Headers(request.headers);
      forwardHeaders.set('X-Forwarded-Host', url.host);
      forwardHeaders.set('X-Forwarded-Proto', url.protocol.replace(':', ''));

      const proxyRequest = new Request(targetUrl.toString(), {
        method: request.method,
        headers: forwardHeaders,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        redirect: 'follow',
      });

      try {
        const response = await fetch(proxyRequest);
        return response;
      } catch (err) {
        return new Response(
          JSON.stringify({
            status: 'offline',
            error: 'Backend API service is currently unreachable or starting up.',
            detail: err.message,
            target: targetUrl.toString(),
          }),
          {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          }
        );
      }
    }

    // Serve static single page application assets
    try {
      const res = await env.ASSETS.fetch(request);
      if (res.status === 404) {
        return await env.ASSETS.fetch(new URL('/', request.url));
      }
      return res;
    } catch (err) {
      return new Response('Not found', { status: 404 });
    }
  },
};

