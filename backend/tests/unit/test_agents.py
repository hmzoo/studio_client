"""Tests unitaires des agents spécialisés (gateway fake)."""
from studio.agents.base import AgentRuntime
from studio.agents.prompt_builder import build_shot_prompt
from studio.agents.reference_analyzer import analyze_reference
from studio.clients.fake_gateway import FakeGenerationGatewayClient
from studio.database import SessionLocal, engine
from studio.domain.models import Base, Character, CompletionProposal, Project, Scene, Shot

Base.metadata.create_all(bind=engine)


def test_prompt_builder_agent():
    db = SessionLocal()
    try:
        gw = FakeGenerationGatewayClient()
        p = Project(name="p")
        db.add(p); db.flush()
        sc = Scene(project_id=p.id, title="s")
        db.add(sc); db.flush()
        sh = Shot(scene_id=sc.id, action="marche sous la pluie", visual_intent="ambiance nuit")
        db.add(sh); db.commit()

        state = build_shot_prompt({"project_id": p.id, "shot_id": sh.id}, AgentRuntime(db=db, gateway=gw))
        assert state["prompt"]
        assert state["reference_image"] is None  # aucun visuel lié
    finally:
        db.close()


def test_analyze_reference_agent_creates_proposal():
    db = SessionLocal()
    try:
        gw = FakeGenerationGatewayClient()
        p = Project(name="p")
        db.add(p); db.flush()
        c = Character(project_id=p.id, name="héros", initial_description="")
        db.add(c); db.commit()

        state = analyze_reference({"project_id": p.id, "kind": "character", "reference_id": c.id},
                                  AgentRuntime(db=db, gateway=gw))
        assert "analysis" in state
        proposals = db.query(CompletionProposal).filter(CompletionProposal.subject_id == c.id).all()
        assert len(proposals) == 1
        assert proposals[0].status == "pending"
    finally:
        db.close()
