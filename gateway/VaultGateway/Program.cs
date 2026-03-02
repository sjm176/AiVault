using Microsoft.AspNetCore.Http;
using System.Net.Http.Headers;

var builder = WebApplication.CreateBuilder(args);

// Enable CORS so your index.html can talk to this API
builder.Services.AddCors(options => options.AddPolicy("AllowAll", p => p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader()));
builder.Services.AddHttpClient();

var app = builder.Build();
app.UseCors("AllowAll");

// Endpoint 1: Receive PDF from Browser -> Forward to Python
app.MapPost("/upload", async (IFormFile file, HttpClient client) => {
    using var content = new MultipartFormDataContent();
    using var stream = file.OpenReadStream();
    var fileContent = new StreamContent(stream);
    fileContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);
    content.Add(fileContent, "file", file.FileName);

    var response = await client.PostAsync("http://localhost:8000/ingest", content);
    return Results.Ok(await response.Content.ReadAsStringAsync());
});

// Endpoint 2: Receive Question from Browser -> Forward to Python
app.MapPost("/chat", async (HttpContext context, HttpClient client) => {
    var query = context.Request.Query["query"];
    var dict = new Dictionary<string, string> { { "question", query } };
    var content = new FormUrlEncodedContent(dict);

    var response = await client.PostAsync("http://localhost:8000/ask", content);
    var result = await response.Content.ReadAsStringAsync();
    return Results.Content(result, "application/json");
});

app.Run("http://localhost:5000");