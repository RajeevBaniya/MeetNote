let currentToken = null;

export const setToken = (token) => {
  currentToken = token;
};

export const getToken = () => currentToken;
