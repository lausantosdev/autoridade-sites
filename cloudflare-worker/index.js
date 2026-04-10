const CORS_HEADERS = {
  "Content-Type": "application/json",
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;

    if (method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    if (method !== "POST") {
      return new Response(
        JSON.stringify({ ok: false, error: "Método não permitido" }),
        { status: 405, headers: CORS_HEADERS }
      );
    }

    const requiredFields = ["nome", "whatsapp", "client_token"];
    let requestBody;
    try {
      requestBody = await request.json();
    } catch (e) {
      return new Response(
        JSON.stringify({ ok: false, error: "Corpo da requisição inválido" }),
        { status: 400, headers: CORS_HEADERS }
      );
    }

    for (const field of requiredFields) {
      if (!requestBody[field]) {
        return new Response(
          JSON.stringify({ ok: false, error: `Campo obrigatório ausente: ${field}` }),
          { status: 400, headers: CORS_HEADERS }
        );
      }
    }

    const supabaseUrl = env.SUPABASE_URL;
    const supabaseKey = env.SUPABASE_SERVICE_KEY;

    // Valida se o client_token existe e está ativo em clientes_perfil
    const tokenCheckUrl = `${supabaseUrl}/rest/v1/clientes_perfil` +
      `?client_token=eq.${encodeURIComponent(requestBody.client_token)}` +
      `&status=eq.live` +
      `&select=id,agency_id`;

    const tokenCheck = await fetch(tokenCheckUrl, {
      headers: {
        apikey: supabaseKey,
        Authorization: `Bearer ${supabaseKey}`,
        Accept: 'application/json',
      },
    });

    const tokenData = await tokenCheck.json();

    if (!Array.isArray(tokenData) || tokenData.length === 0) {
      return new Response(
        JSON.stringify({ ok: false, error: 'Token inválido ou site inativo' }),
        { status: 403, headers: CORS_HEADERS }
      );
    }

    // Enriquecer o payload com agency_id para rastreabilidade futura
    requestBody.agency_id = tokenData[0].agency_id;

    // Insere lead no Supabase
    const insertUrl = `${supabaseUrl}/rest/v1/leads`;
    const response = await fetch(insertUrl, {
      method: "POST",
      headers: {
        apikey: supabaseKey,
        Authorization: `Bearer ${supabaseKey}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(requestBody),
    });

    if (!response.ok) {
      return new Response(
        JSON.stringify({ ok: false, error: "Erro ao salvar lead" }),
        { status: 500, headers: CORS_HEADERS }
      );
    }

    // Sucesso
    return new Response(
      JSON.stringify({ ok: true }),
      { status: 200, headers: CORS_HEADERS }
    );
  },
};