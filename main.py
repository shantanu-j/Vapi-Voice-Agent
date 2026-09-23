from fastapi import FastAPI
from src.api.routes import appointments, availability, complaints, health
from src.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Statfinity AI Voice Assistant",
    description="Backend API for the Statfinity AI voice assistant.",
    version="1.0.0",
)


app.include_router(health.router)
app.include_router(appointments.router)
app.include_router(availability.router)
app.include_router(complaints.router)