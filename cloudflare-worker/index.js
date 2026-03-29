export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;

    // Responde a requisições OPTIONS (preflight CORS)
    if (method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    // Apenas métodos POST são permitidos
    if (method !== "POST") {
      return new Response(
        JSON.stringify({ ok: false, error: "Método não permitido" }),
        {
          status: 405,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
          },
        }
      );
    }

    // Valida campos obrigatórios
    const requiredFields = ["nome", "whatsapp", "client_token"];
    let requestBody;
    try {
      requestBody = await request.json();
    } catch (e) {
      return new Response(
        JSON.stringify({ ok: false, error: "Corpo da requisição inválido" }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
          },
        }
      );
    }

    for (const field of requiredFields) {
      if (!requestBody[field]) {
        return new Response(
          JSON.stringify({ ok: false, error: `Campo obrigatório ausente: ${field}` }),
          {
            status: 400,
            headers: {
              "Content-Type": "application/json",
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type",
            },
          }
        );
      }
    }

    // Insere lead no Supabase
    const supabaseUrl = env.SUPABASE_URL;
    const supabaseKey = env.SUPABASE_SERVICE_KEY;
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
        {
          status: 500,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
          },
        }
      );
    }

    // Sucesso
    return new Response(
      JSON.stringify({ ok: true }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      }
    );
  },
};