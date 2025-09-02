export interface User {
  id: string;
  name: string;
  email: string;
  picture: string;
}

export interface AuthData {
  access_token: string;
  user: User;
}

export interface Booking {
  id: string;
  name: string;
  email: string;
  schedule_date: string;
  schedule_time: string;
  created_at: string;
}

export type MessageType = {
  text: string;
  ai_response:string;
  source: string;
  sender: string;
  audioBlob?: Blob;
  audioUrl?: string;
  isVoiceMessage?: boolean;
};

export interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

export interface GoogleUser {
  iss: string;
  azp: string;
  aud: string;
  sub: string;
  email: string;
  email_verified: boolean;
  nbf: number;
  name: string;
  picture: string;
  given_name: string;
  family_name: string;
  locale: string;
  iat: number;
  exp: number;
  jti: string;
}