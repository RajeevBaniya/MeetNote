import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET;

if (!JWT_SECRET || !JWT_SECRET.trim()) {
  throw new Error("JWT_SECRET environment variable is required");
}

export function authenticateJwt(req, res, next) {
  const header = req.headers.authorization || "";
  const [scheme, token] = header.split(" ");

  if (!token || scheme !== "Bearer") {
    return res.status(401).json({ error: "Unauthorized" });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET.trim());
    const subject = decoded && typeof decoded.sub === "string" ? decoded.sub : null;

    if (!subject) {
      return res.status(401).json({ error: "Unauthorized" });
    }

    req.user = { id: subject };
    return next();
  } catch (err) {
    console.error("JWT validation failed:", err.message || err);
    return res.status(401).json({ error: "Unauthorized" });
  }
}

