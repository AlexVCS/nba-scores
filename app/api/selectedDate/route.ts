import { NextApiRequest, NextApiResponse } from "next";

export default function handler(req: NextApiRequest,
  res: NextApiResponse) {
  const { selectedDate } = req.query;
  res.status(200).json({ selectedDate });
}