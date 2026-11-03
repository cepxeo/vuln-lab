package com.harborline.claimdesk.web;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Trivial in-memory session store keyed by an opaque cookie value. */
public final class Sessions {
    public static final class User {
        public long id;
        public String username;
        public String role;
        public String fullName;
    }

    private static final Map<String, User> STORE = new ConcurrentHashMap<>();

    public static String put(User u) {
        String sid = Long.toHexString(Double.doubleToLongBits(Math.random())) +
                     Long.toHexString(System.nanoTime());
        STORE.put(sid, u);
        return sid;
    }

    public static User get(String sid) {
        return sid == null ? null : STORE.get(sid);
    }

    public static void drop(String sid) {
        if (sid != null) STORE.remove(sid);
    }
}
