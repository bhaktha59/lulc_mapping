export default {
  async fetch(request, env) {
    try {
      const res = await env.ASSETS.fetch(request);
      if (res.status === 404) {
        return await env.ASSETS.fetch(new URL("/", request.url));
      }
      return res;
    } catch (err) {
      return new Response("Not found", { status: 404 });
    }
  },
};
