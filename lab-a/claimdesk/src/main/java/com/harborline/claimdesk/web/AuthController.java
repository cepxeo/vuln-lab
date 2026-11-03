package com.harborline.claimdesk.web;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;

import javax.servlet.http.Cookie;
import javax.servlet.http.HttpServletResponse;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

@Controller
public class AuthController {

    @Autowired
    private JdbcTemplate jdbc;

    @GetMapping("/")
    public String root(@CookieValue(value = "SID", required = false) String sid) {
        return Sessions.get(sid) != null ? "redirect:/dashboard" : "redirect:/login";
    }

    @GetMapping("/login")
    public String loginForm() {
        return "login";
    }

    // The sign-in form. There is no password policy, so weak passwords are
    // accepted both here and at registration. Passwords are stored as unsalted
    // MD5. The username is concatenated straight into the SQL string.
    @PostMapping("/login")
    public String login(@RequestParam String username,
                        @RequestParam String password,
                        HttpServletResponse resp,
                        Model model) {
        String md5 = md5(password);
        String sql = "SELECT id, username, role, full_name FROM users " +
                     "WHERE username = '" + username + "' AND password = '" + md5 + "'";
        try {
            List<Map<String, Object>> rows = jdbc.queryForList(sql);
            if (rows.isEmpty()) {
                model.addAttribute("error", "Invalid credentials");
                return "login";
            }
            Map<String, Object> r = rows.get(0);
            Sessions.User u = new Sessions.User();
            u.id = ((Number) r.get("id")).longValue();
            u.username = String.valueOf(r.get("username"));
            u.role = String.valueOf(r.get("role"));
            u.fullName = String.valueOf(r.get("full_name"));
            Cookie c = new Cookie("SID", Sessions.put(u));
            c.setPath("/");
            resp.addCookie(c);
            return "redirect:/dashboard";
        } catch (Exception e) {
            // verbose: the failing SQL is shown back to the client
            model.addAttribute("error", "Query failed: " + e.getMessage() + " [" + sql + "]");
            return "login";
        }
    }

    @GetMapping("/register")
    public String registerForm() {
        return "register";
    }

    // Self-registration with no password-strength check at all.
    @PostMapping("/register")
    public String register(@RequestParam String username,
                          @RequestParam String password,
                          @RequestParam(required = false) String email,
                          Model model) {
        try {
            jdbc.update("INSERT INTO users(username, password, full_name, email, role) " +
                        "VALUES (?,?,?,?, 'customer')",
                        username, md5(password), username, email);
            model.addAttribute("ok", "Account created. You can sign in.");
        } catch (Exception e) {
            model.addAttribute("error", e.getMessage());
        }
        return "login";
    }

    @GetMapping("/logout")
    public String logout(@CookieValue(value = "SID", required = false) String sid) {
        Sessions.drop(sid);
        return "redirect:/login";
    }

    static String md5(String s) {
        try {
            MessageDigest d = MessageDigest.getInstance("MD5");
            byte[] h = d.digest(s.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte b : h) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }
}
