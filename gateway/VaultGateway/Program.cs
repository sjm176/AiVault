using Microsoft.AspNetCore.Http;
using System.Net.Http.Headers;

var builder = WebApplication.CreateBuilder(args);

// 1. Setup Services
builder.Services.AddCors(options => options.AddPolicy("AllowAll", p => p.AllowAnyOrigin().AllowAnyMethod().AllowAnyHeader()));

// 2. Configure HttpClient with a longer timeout for Local AI (Free Brain)
builder.Services.AddHttpClient("BrainClient", client => {
    client.BaseAddress = new Uri("http://localhost:8000/");
    client.Timeout = TimeSpan.FromSeconds(60); // Gives Local AI time to think
});

builder.Services.AddAntiforgery();

var app = builder.Build();

app.UseCors("AllowAll");
app.UseAntiforgery();

// ENDPOINT 1: UPLOAD
app.MapPost("/upload", async (IFormFile file, IHttpClientFactory factory) => {
    var client = factory.CreateClient("BrainClient");
    
    using var content = new MultipartFormDataContent();
    using var stream = file.OpenReadStream();
    var fileContent = new StreamContent(stream);
    fileContent.Headers.ContentType = new MediaTypeHeaderValue(file.ContentType);
    content.Add(fileContent, "file", file.FileName);

    try {
        var response = await client.PostAsync("ingest", content);
        var result = await response.Content.ReadAsStringAsync();
        return Results.Ok(result);
    } catch (Exception ex) {
        return Results.Problem($"Brain unreachable: {ex.Message}");
    }
}).DisableAntiforgery();

// ENDPOINT 2: CHAT
app.MapPost("/chat", async (HttpContext context, IHttpClientFactory factory) => {
    var client = factory.CreateClient("BrainClient");
    
    // Fixes the Null Warning: ensures query isn't null
    string query = context.Request.Query["query"].ToString() ?? "No question provided";
    
    var dict = new Dictionary<string, string> { { "question", query } };
    var content = new FormUrlEncodedContent(dict);

    try {
        var response = await client.PostAsync("ask", content);
        var result = await response.Content.ReadAsStringAsync();
        return Results.Content(result, "application/json");
    } catch (Exception ex) {
        return Results.Problem($"AI is currently offline: {ex.Message}");
    }
}).DisableAntiforgery();

app.Run("http://localhost:5000");